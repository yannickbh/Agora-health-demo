from agora_token_builder import RtcTokenBuilder
import time
import base64
import httpx
from fastapi import HTTPException
from ..config import get_settings

def generate_rtc_token(channel: str, uid: int) -> str:
    settings = get_settings()
    return RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID, settings.AGORA_APP_CERT, channel, uid,
        1,  # 1 = Role_Publisher
        int(time.time()) + 3600
    )

def get_convoai_base_url() -> str:
    settings = get_settings()
    return f"https://api.agora.io/api/conversational-ai-agent/v2/projects/{settings.AGORA_APP_ID}"

def get_convoai_headers() -> dict:
    settings = get_settings()
    auth_user = settings.AGORA_CUSTOMER_ID or settings.AGORA_APP_ID
    auth_pass = settings.AGORA_CUSTOMER_SECRET or settings.AGORA_APP_CERT
    auth_str = base64.b64encode(f"{auth_user}:{auth_pass}".encode()).decode()
    return {"Authorization": f"Basic {auth_str}", "Content-Type": "application/json"}

def get_tts_config():
    settings = get_settings()
    tts_vendor = "microsoft"
    tts_voice = settings.TTS_VOICE
    
    if not settings.AZURE_TTS_KEY or "your_azure" in settings.AZURE_TTS_KEY:
        tts_vendor = "openai"
        tts_voice = "shimmer" if "Jenny" in settings.TTS_VOICE or "Francisca" in settings.TTS_VOICE else "alloy"
        
    return tts_vendor, tts_voice
