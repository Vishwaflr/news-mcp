from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str = "postgresql://user:password@localhost:5432/db_name"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    mcp_port: int = 8001
    log_level: str = "INFO"
    debug: bool = False
    fetch_interval_minutes: int = 15
    max_concurrent_fetches: int = 10

    # LLM Analysis Configuration
    openai_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    analysis_model: str = "gpt-4o-mini"
    analysis_batch_limit: int = 200
    analysis_rps: float = 1.0

    # Analysis Run Manager Configuration
    max_concurrent_runs: int = 5
    max_daily_runs: int = 100
    max_daily_auto_runs: int = 500
    max_hourly_runs: int = 10
    auto_analysis_rate_per_second: float = 3.0

    # MCP v2 Configuration
    mcp_server_readonly: bool = False
    mcp_api_base_url: str = "http://localhost:8000"
    mcp_rate_limit: str = "100/min"
    analysis_model_costs: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()