import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(PROJECT_ROOT, "configs", "display.json")

DEFAULT_CONFIG = {
    "storage": {
        "max_entries": 100
    },
    "history": {
        "display_limit": 100
    },
    "logs": {
        "page_size": 10,
        "message_width": 30,
        "details_width": 70
    }
}


class AppConfig:
    @staticmethod
    def load():
        config = DEFAULT_CONFIG.copy()

        if not os.path.exists(CONFIG_FILE):
            return config

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_config = json.load(f)
        except json.JSONDecodeError:
            return config

        for section, values in file_config.items():
            if isinstance(values, dict) and isinstance(config.get(section), dict):
                config[section] = {**config[section], **values}
            else:
                config[section] = values

        return config

    @staticmethod
    def get(section, key, default=None):
        return AppConfig.load().get(section, {}).get(key, default)
