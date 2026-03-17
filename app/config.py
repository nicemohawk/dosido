from pydantic import field_validator
from pydantic_settings import BaseSettings

VALID_THEMES = (
    "obsidian",
    "claude",
    "noir",
    "carbon",
    "deep-space",
    "emerald",
    "sunset",
    "terminal",
    "arctic",
)

THEME_FONT_URLS: dict[str, str] = {
    "obsidian": "Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700;800",
    "claude": "DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700;800",
    "noir": "Cormorant+Garamond:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700;800",
    "carbon": "Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700;800",
    "deep-space": "Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700;800",
    "emerald": "Lora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700;800",
    "sunset": "Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700;800",
    "terminal": "Fira+Code:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700;800",
    "arctic": (
        "Instrument+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600;700"
        "&family=JetBrains+Mono:wght@400;500;700;800"
    ),
}


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    anthropic_api_key: str = ""

    event_slug: str = "climate-week-2026"
    event_name: str = "SF Climate Week Dosido"
    admin_token: str = ""
    base_url: str = "http://localhost:8000"

    round_duration_minutes: int = 8
    total_rounds: int = 10

    # UI theme — see app/static/css/themes/ for available options
    theme: str = "obsidian"

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        if value not in VALID_THEMES:
            raise ValueError(f"Unknown theme '{value}'. Valid themes: {', '.join(VALID_THEMES)}")
        return value

    @property
    def theme_font_url(self) -> str:
        families = THEME_FONT_URLS.get(self.theme, THEME_FONT_URLS["obsidian"])
        return f"https://fonts.googleapis.com/css2?family={families}&display=swap"

    # LLM provider: "claude", "ollama", or "none"
    llm_provider: str = "claude"
    ollama_model: str = "llama3.2"
    ollama_url: str = "http://localhost:11434"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
