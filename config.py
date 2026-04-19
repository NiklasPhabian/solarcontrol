import configparser
from pathlib import Path
from typing import Optional

CONFIG_FILE_NAME = "config.ini"
KASA_SECTION = "kasa"
SQLITE_SECTION = "sqlite"
DEFAULT_SQLITE_DB_FILE = "pv_realtime.db"
DEFAULT_SQLITE_TABLE_NAME = "realtime"


class Config:
    def __init__(self, config_path='config.ini'):
        self.config_path = Path(config_path) 
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}. Create {CONFIG_FILE_NAME} in the project root."
            )
        self._parser = configparser.ConfigParser()
        self.config = {}
        self._parser.read(self.config_path)
        self.read()


    def __repr__(self):
        return self.config
    
    def __str__(self):
        return str(self.__repr__())

    def read(self):
        for section in self._parser.sections():
            self.config[section] = dict(self._parser[section])
        return self.config

    def __getitem__(self, key):
        return self.config[key]


if __name__ == "__main__":
    config = Config('config.ini')
    print(config['kasa'])
    