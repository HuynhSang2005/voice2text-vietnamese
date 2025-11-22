from typing import List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Real-time Vietnamese STT"
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]
    MODEL_STORAGE_PATH: str = "models_storage"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
