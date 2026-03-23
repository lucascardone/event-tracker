from pathlib import Path
import yaml

_config_path = Path(__file__).parent.parent / "config.yaml"
_raw = yaml.safe_load(_config_path.read_text())

_db = _raw["db"]


class Settings:
    database_url: str = (
        f"postgresql+asyncpg://{_db['user']}:{_db['passwd']}"
        f"@{_db['host']}:{_db['port']}/{_db['name']}"
    )
    redis_url: str = _raw.get("redis_url", "redis://localhost:6379/0")
    redis_ttl_seconds: int = _raw.get("redis_ttl_seconds", 86400)


settings = Settings()