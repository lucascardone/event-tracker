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
    connect_args: dict = {"statement_cache_size": 0}


settings = Settings()