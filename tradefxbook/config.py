"""
TradeFXBook Configuration Settings.
Provides central settings for database paths, deterministic seeding parameters,
default reference dates, and application secrets.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRADEFXBOOK_")

    # Base paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = Path(__file__).resolve().parent / "data"
    DB_PATH: Path = DATA_DIR / "tradefxbook.db"

    # Demo Dataset specifications
    DEMO_USERS_COUNT: int = 10
    DEMO_TRADES_PER_USER: int = 10_000
    TOTAL_DEMO_TRADES: int = 100_000
    DEMO_SEED_BATCH: str = "tradefxbook_demo_batch_v1"
    RANDOM_SEED: int = 42

    # Deterministic reference end date for demo generation (ISO format UTC)
    # Using fixed date so re-seeding produces identical dataset regardless of system time
    REFERENCE_END_DATE: str = "2026-10-25T00:00:00Z"
    DEMO_HISTORY_DAYS: int = 730  # ~2 years of historical trades

    # Security
    SECRET_KEY: str = "tradefxbook-super-secret-demo-key-2026-safe-production"
    ALGORITHM: str = "HS256"
    DEMO_PASSWORD_SALT: str = "tradefxbook_demo_salt_2026"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    def ensure_data_dir(self) -> Path:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return self.DATA_DIR


settings = Settings()
