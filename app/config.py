from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str = "postgresql://news_user:news_password@localhost:5432/news_db"
    api_host: str = "192.168.178.72"
    api_port: int = 8000
    mcp_port: int = 8001
    log_level: str = "INFO"
    fetch_interval_minutes: int = 15
    max_concurrent_fetches: int = 10

    class Config:
        env_file = ".env"

settings = Settings()