import logging.config
import os
from pathlib import Path

import toml
import yaml
from dotenv import load_dotenv

from .utils.dotdict import DotDict

__all__ = ["STATIC_DIR", "CONFIG"]

_BOT_DIR = Path(__file__).parent
STATIC_DIR = _BOT_DIR / "static"
with open(_BOT_DIR.parent / "bot-config.yaml", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)  # Global dict which contains bot config


def setup():
    load_dotenv()  # Loads .env file by default
    log_config = DotDict(toml.load(_BOT_DIR.parent / "log-config.toml"))

    if os.getenv("ENVIRONMENT") == "development":
        # All logger are inherited from the root logger
        log_config.loggers.root = log_config.loggers.development

    # Create logs in current directory, does anything if it already exists
    os.makedirs("logs", exist_ok=True)
    logging.config.dictConfig(log_config)  # Loads config


setup()
