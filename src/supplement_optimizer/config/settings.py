"""Application settings, loaded from environment / .env via pydantic-settings.

Secrets are *never* hardcoded. In local development they come from a git-ignored
``.env`` file; in CI they are injected from GitHub Secrets. Optional secrets
default to ``None`` so the core (optimizer/reports) runs without any of them.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from supplement_optimizer.domain.enums import Currency


class Settings(BaseSettings):
    """Strongly-typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Supabase (all optional so the core works offline) ---
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None

    # --- Optimization defaults ---
    optimizer_destination_country: str = Field(default="SK", min_length=2, max_length=2)
    optimizer_base_currency: Currency = Currency.EUR

    # --- Scraping ---
    playwright_browsers_path: str = "default"
    scraper_user_agent: str = "supplement-optimizer/0.1 (+https://github.com/ToxicMinds/Web-Scr)"
    scraper_request_timeout_seconds: float = 30.0
    scraper_max_concurrency: int = 4

    # --- Notifications ---
    notification_webhook: SecretStr | None = None

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = True

    @property
    def supabase_configured(self) -> bool:
        """Whether enough Supabase settings are present to connect."""
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, process-wide :class:`Settings` instance."""
    return Settings()
