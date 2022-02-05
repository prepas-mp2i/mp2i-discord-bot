import logging.config
import os
from pathlib import Path

import toml
from dotenv import load_dotenv

__all__ = ["STATIC_DIR"]

_BOT_DIR = Path(__file__).parent
STATIC_DIR = _BOT_DIR / "static"


def setup():
    load_dotenv()  # Loads .env file by default
    log_config = toml.load(_BOT_DIR.parent / "log-config.toml")

    if os.getenv("ENVIRONMENT") == "development":
        # All logger are inherited from the root logger
        log_config["loggers"]["root"] = log_config["loggers"]["development"]

    # Create logs in current directory, does anything if it already exists
    os.makedirs("logs", exist_ok=True)
    logging.config.dictConfig(log_config)  # Loads config


setup()
