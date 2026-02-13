from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    anthropic_api_key: str = ""

    event_slug: str = "climate-week-2026"
    event_name: str = "SF Climate Week Cofounder Matchmaking"
    admin_token: str = "change-me"
    base_url: str = "http://localhost:8000"

    round_duration_minutes: int = 8
    total_rounds: int = 10

    # LLM provider: "claude", "ollama", or "none"
    llm_provider: str = "claude"
    ollama_model: str = "llama3.2"
    ollama_url: str = "http://localhost:11434"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
