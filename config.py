import configparser
from pathlib import Path
from typing import Optional

CONFIG_FILE_NAME = "config.ini"
KASA_SECTION = "kasa"
SQLITE_SECTION = "sqlite"
DEFAULT_SQLITE_DB_FILE = "pv_realtime.db"
DEFAULT_SQLITE_TABLE_NAME = "realtime"


class Config:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (Path(__file__).parent / CONFIG_FILE_NAME)
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}. Create {CONFIG_FILE_NAME} in the project root."
            )
        self._parser = configparser.ConfigParser()
        self._parser.read(self.config_path)

    def get_kasa_credentials(self) -> dict[str, str]:
        if KASA_SECTION not in self._parser:
            raise ValueError(f"Missing [{KASA_SECTION}] section in {CONFIG_FILE_NAME}")

        section = self._parser[KASA_SECTION]
        username = section.get("username")
        password = section.get("password")

        if not username or not password:
            raise ValueError(
                f"{CONFIG_FILE_NAME} must contain username and password in the [{KASA_SECTION}] section"
            )

        return {"username": username, "password": password}

    def get_sqlite_db_path(self) -> Path:
        db_path = Path(self._parser.get(SQLITE_SECTION, "db_file", fallback=DEFAULT_SQLITE_DB_FILE)).expanduser()
        if not db_path.is_absolute():
            db_path = (self.config_path.parent / db_path).resolve()
        return db_path

    def get_realtime_table_name(self) -> str:
        return self._parser.get(SQLITE_SECTION, "table_name", fallback=DEFAULT_SQLITE_TABLE_NAME).strip() or DEFAULT_SQLITE_TABLE_NAME


def load_config(config_path: Optional[Path] = None) -> Config:
    return Config(config_path)
