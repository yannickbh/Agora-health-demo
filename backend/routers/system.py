from fastapi import APIRouter
from ..config import get_settings
from ..services.agora import generate_rtc_token
from .agent import get_active_agents, list_use_cases

router = APIRouter()

@router.get("/token/{channel}/{uid}")
def get_user_token(channel: str, uid: int):
    print(f">>> [GET /token] Channel: {channel}, UID: {uid}")
    return {"token": generate_rtc_token(channel, uid), "channel": channel, "uid": uid}

@router.get("/config")
def get_public_config():
    settings = get_settings()
    return {"agora_app_id": settings.AGORA_APP_ID}

@router.get("/use_cases")
def get_use_cases():
    return {"use_cases": list_use_cases()}

@router.get("/status")
def status():
    active_agents = get_active_agents()
    settings = get_settings()
    return {
        "active_channels": list(active_agents.keys()),
        "count": len(active_agents),
        "app_id_configured": bool(settings.AGORA_APP_ID),
    }

@router.get("/health")
def health():
    return {"status": "ok"}
