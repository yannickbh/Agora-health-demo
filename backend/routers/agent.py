from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from ..config import get_settings
from ..services.agora import generate_rtc_token, get_convoai_base_url, get_convoai_headers, get_tts_config
import os
import pathlib

router = APIRouter()

active_agents: dict[str, str] = {}

class StartRequest(BaseModel):
    channel: str = "hospital-support"
    user_uid: int = 1

def load_system_prompt() -> str:
    base_dir = pathlib.Path(__file__).parent.parent
    kb_path = base_dir / "data" / "knowledge_base.md"
    prompt_path = base_dir / "data" / "prompts.txt"
    with open(kb_path, "r", encoding="utf-8") as f:
        kb_content = f.read()
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_content = f.read()
    return prompt_content.replace("{knowledge_base}", kb_content)

@router.post("/start")
async def start_agent(req: StartRequest):
    settings = get_settings()
    print(f">>> [POST /start] Channel: {req.channel}, UID: {req.user_uid}")
    if req.channel in active_agents:
        return {"status": "already_running", "agent_id": active_agents[req.channel]}

    agent_token = generate_rtc_token(req.channel, uid=int(settings.AGENT_UID))  # Must match agent_rtc_uid

    tts_vendor, tts_voice = get_tts_config()
    system_prompt = load_system_prompt()
    tts_params = {
        "key": settings.AZURE_TTS_KEY,
        "region": settings.AZURE_TTS_REGION,
        "voice_name": tts_voice,
    } if tts_vendor == "microsoft" else {
        "api_key": settings.OPENAI_API_KEY,
        "model": "tts-1",
        "voice": tts_voice,
        "base_url": "https://api.openai.com/v1",
        "speed": 1.0,
    }

    payload = {
        "name": f"hospital-agent-{req.channel}-{int(__import__('time').time())}",  # Must be unique per invocation
        "properties": {
            "channel": req.channel,
            "token": agent_token,
            "agent_rtc_uid": settings.AGENT_UID,  # Non-zero string UID for the agent
            "remote_rtc_uids": [str(req.user_uid)],
            "enable_string_uid": False,
            "idle_timeout": 30,
            "asr": {
                "language": settings.AGENT_LANGUAGE,
                "task": "conversation",
            },
            "llm": {
                "url": "https://api.openai.com/v1/chat/completions",
                "api_key": settings.OPENAI_API_KEY,
                "system_messages": [{"role": "system", "content": system_prompt}],
                "greeting_message": "Olá! Sou o Assistente Hospitalar. Como posso ajudá-lo?",
                "failure_message": "Desculpe, não consegui processar. Tente novamente.",
                "max_history": 10,
                "params": {
                    "model": settings.LLM_MODEL,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                    "top_p": 0.95,
                },
                "input_modalities": ["text"],
                "output_modalities": ["text"],
            },
            "tts": {
                "vendor": tts_vendor,
                "params": tts_params,
            },
            "vad": {
                "silence_duration_ms": 480,
                "speech_duration_ms": 15000,
                "threshold": 0.5,
                "interrupt_duration_ms": 160,
                "prefix_padding_ms": 300,
            },
            "advanced_features": {
                "enable_aivad": False,
                "enable_bhvs": False,
            },
        },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(f"{get_convoai_base_url()}/join", headers=get_convoai_headers(), json=payload)
            if resp.status_code != 200:
                error_msg = f"Agora API Error {resp.status_code}: {resp.text}"
                print(f"!!! {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
            
            resp.raise_for_status()
            data = resp.json()
        except httpx.RequestError as e:
            print(f"!!! Network Error contacting Agora: {e}")
            raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            print(f"!!! Unexpected error starting Agora agent: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    active_agents[req.channel] = data["agent_id"]
    return {"status": "started", "agent_id": data["agent_id"], "channel": req.channel}

@router.post("/stop/{channel}")
async def stop_agent(channel: str):
    agent_id = active_agents.pop(channel, None)
    if not agent_id:
        raise HTTPException(404, f"No active agent on channel '{channel}'")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{get_convoai_base_url()}/agents/{agent_id}/leave", headers=get_convoai_headers()
        )
        resp.raise_for_status()

    return {"status": "stopped", "agent_id": agent_id}

def get_active_agents():
    return active_agents
