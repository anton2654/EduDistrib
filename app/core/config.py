from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            environ.setdefault(key, value)


def _to_bool(value: str, default: bool = False) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _to_csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str
    debug: bool
    database_url: str
    cors_origins: tuple[str, ...]
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    db_init_on_startup: bool
    db_startup_strict: bool

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        return cls(
            app_name=getenv("APP_NAME", "Distributor API"),
            debug=_to_bool(getenv("DEBUG", "false")),
            database_url=getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://postgres:postgres@localhost:5432/distributor",
            ),
            cors_origins=_to_csv_tuple(
                getenv(
                    "CORS_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173",
                ),
            ),
            jwt_secret_key=getenv("JWT_SECRET_KEY", "change-me-in-production"),
            jwt_algorithm=getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=_to_int(
                getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"),
                default=60,
            ),
            db_init_on_startup=_to_bool(getenv("DB_INIT_ON_STARTUP", "false"), default=False),
            db_startup_strict=_to_bool(getenv("DB_STARTUP_STRICT", "false"), default=False),
        )


settings = Settings.from_env()