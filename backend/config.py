from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    AGORA_APP_ID: str = ""
    AGORA_APP_CERT: str = ""
    AGORA_CUSTOMER_ID: str = ""
    AGORA_CUSTOMER_SECRET: str = ""
    OPENAI_API_KEY: str = ""
    AZURE_TTS_KEY: str = ""
    AZURE_TTS_REGION: str = "eastus"
    AGENT_LANGUAGE: str = "pt-BR"
    TTS_VOICE: str = "pt-BR-FranciscaNeural"
    AGENT_UID: str = "9999"     # Non-zero UID for the AI agent in the RTC channel
    LLM_MODEL: str = "gpt-4o"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()
