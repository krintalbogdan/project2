from typing import List
import os
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    API_PREFIX: str = "/api"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///database.db"
    STATIC_URL: str = os.getcwd() + "/static"

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:3000" 


    @field_validator("ALLOWED_ORIGINS")
    def parse_allowed_origins(cls, v: str) -> List[str]:
        return v.split(",") if v else []
    

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()