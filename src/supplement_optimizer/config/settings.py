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
    scraper_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    scraper_request_timeout_seconds: float = 30.0
    scraper_max_concurrency: int = 4
    #: When True, live plugins hit their real APIs; when False (default) they use
    #: their deterministic offline seed catalog. The nightly/weekly workflows set
    #: this True so production reports contain real prices; tests/CI stay offline.
    scraper_live: bool = False
    #: Optional CA bundle path for environments behind a TLS-intercepting proxy.
    #: Falls back to the ``SSL_CERT_FILE`` env var, then to normal verification.
    scraper_ca_bundle: str | None = None

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
