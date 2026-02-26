from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import json
import time
import pathlib
from ..config import get_settings
from ..services.agora import generate_rtc_token, get_convoai_base_url, get_convoai_headers, get_tts_config

router = APIRouter()

active_agents: dict[str, str] = {}

USE_CASES_DIR = pathlib.Path(__file__).parent.parent / "data" / "use_cases"

class StartRequest(BaseModel):
    channel: str = "hospital-support"
    user_uid: int = 1
    use_case: str = "hospital"


def load_use_case(use_case: str) -> dict:
    """Load config.json and knowledge_base.md for a given use case."""
    use_case_dir = USE_CASES_DIR / use_case
    config_path = use_case_dir / "config.json"
    kb_path = use_case_dir / "knowledge_base.md"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Use case '{use_case}' not found.")

    config = json.loads(config_path.read_text(encoding="utf-8"))

    kb_content = ""
    if kb_path.exists():
        kb_content = kb_path.read_text(encoding="utf-8")

    system_prompt = config["prompt"]
    if kb_content:
        system_prompt += f"\n\n{kb_content}"

    return {
        "system_prompt": system_prompt,
        "language": config.get("language", "pt-BR"),
        "voice": config.get("voice", "pt-BR-FranciscaNeural"),
        "greeting": config.get("greeting", "Olá! Como posso ajudá-lo?"),
        "failure_message": config.get("failure_message", "Desculpe, tente novamente."),
        "name": config.get("name", use_case),
    }


def list_use_cases() -> list[dict]:
    """Return all available use cases with their display names."""
    if not USE_CASES_DIR.exists():
        return []
    result = []
    for d in sorted(USE_CASES_DIR.iterdir()):
        if not d.is_dir():
            continue
        config_path = d / "config.json"
        if not config_path.exists():
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        result.append({"id": d.name, "name": config.get("name", d.name)})
    return result


@router.post("/start")
async def start_agent(req: StartRequest):
    settings = get_settings()
    print(f">>> [POST /start] Channel: {req.channel}, UID: {req.user_uid}, Use case: {req.use_case}")

    if req.channel in active_agents:
        return {"status": "already_running", "agent_id": active_agents[req.channel]}

    uc = load_use_case(req.use_case)

    agent_token = generate_rtc_token(req.channel, uid=int(settings.AGENT_UID))

    tts_vendor, _ = get_tts_config()
    tts_voice = uc["voice"]

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
        "name": f"agent-{req.use_case}-{req.channel}-{int(time.time())}",
        "properties": {
            "channel": req.channel,
            "token": agent_token,
            "agent_rtc_uid": settings.AGENT_UID,
            "remote_rtc_uids": [str(req.user_uid)],
            "enable_string_uid": False,
            "idle_timeout": 30,
            "asr": {
                "language": uc["language"],
                "task": "conversation",
            },
            "llm": {
                "url": "https://api.openai.com/v1/chat/completions",
                "api_key": settings.OPENAI_API_KEY,
                "system_messages": [{"role": "system", "content": uc["system_prompt"]}],
                "greeting_message": uc["greeting"],
                "failure_message": uc["failure_message"],
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
    return {"status": "started", "agent_id": data["agent_id"], "channel": req.channel, "use_case": req.use_case}


@router.post("/stop/{channel}")
async def stop_agent(channel: str):
    agent_id = active_agents.get(channel)
    if not agent_id:
        raise HTTPException(404, f"No active agent on channel '{channel}'")

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(
                f"{get_convoai_base_url()}/agents/{agent_id}/leave", headers=get_convoai_headers()
            )
            resp.raise_for_status()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Network error stopping agent: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=500, detail=f"Agora API error stopping agent: {str(e)}")

    active_agents.pop(channel, None)
    return {"status": "stopped", "agent_id": agent_id}


def get_active_agents():
    return active_agents
