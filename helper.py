import os
import sys
from pathlib import Path

import yaml
from logger import logger
from sqlalchemy import create_engine, inspect

CONFIG_FILE_PATH = "config/config.yaml"


class ConfigManager:
    def __init__(self, config_file_path=CONFIG_FILE_PATH):
        self.config_file_path = config_file_path
        self.config_dict = {
            "connection_string": "mysql+pymysql://username:password@ip:3306/db?charset=utf8mb4",
            "wan_adr": "",
            "transaction_table": "",
            "koinly_table": "",
            "rows": "",
            "private_key": "",
            "api_key": "",
        }
        self.config = None
        self._ensure_config_file()

    def _ensure_config_file(self):
        if not os.path.exists(self.config_file_path):
            Path(self.config_file_path).parent.mkdir(parents=True, exist_ok=True)
            Path(self.config_file_path).touch()
            logger.info("Config file created")
            self._write_config_file()
        else:
            logger.info("Config file already exists")

    def _write_config_file(self):
        with open(self.config_file_path, "w") as ymlfile:
            yaml.dump(self.config_dict, ymlfile, default_flow_style=False)

    def load_config(self):
        self._ensure_config_file()
        try:
            with open(self.config_file_path, "r") as ymlfile:
                self.config = yaml.safe_load(ymlfile)
                logger.info("Yaml file correctly loaded")
        except yaml.YAMLError as exc:
            logger.error("Error in config file:", exc)
            raise
        return self.config

    def apply_config(self):
        if not self.config:
            self.load_config()
        try:
            connection_string = self.config["connection_string"]
            transaction_table = self.config["transaction_table"]
            koinly_table = self.config["koinly_table"]
            wan_adr = self.config["wan_adr"]
            rows = self.config["rows"]
            private_key = self.config["private_key"]
            api_key = self.config["api_key"]
            logger.info("All settings loaded correctly")
        except KeyError as exc:
            logger.error("Error loading config", exc)
            raise
        return (
            connection_string,
            transaction_table,
            koinly_table,
            wan_adr,
            rows,
            private_key,
            api_key,
        )

    def transactions_check(self, connection_string, transaction_table):
        try:
            engine = create_engine(connection_string)
            inspector = inspect(engine)
            return not inspector.has_table(transaction_table)
        except Exception as exc:
            logger.error(
                "Error connecting to database - Please check configuration",
                exc_info=True,
            )
            sys.exit()
