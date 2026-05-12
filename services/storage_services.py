import json
import os
from datetime import datetime

from services.app_config import AppConfig, PROJECT_ROOT

WORKSPACE_ROOT = os.path.dirname(PROJECT_ROOT)
WORKSPACE_DATA_ROOT = os.path.join(WORKSPACE_ROOT, "data")
PROJECT_DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
DATA_ROOT = WORKSPACE_DATA_ROOT if os.path.exists(WORKSPACE_DATA_ROOT) else PROJECT_DATA_ROOT

class StorageService:
    def __init__(self, filepath):
        self.filepath = self._resolve_filepath(filepath)
        self.max_entries = AppConfig.get("storage", "max_entries", 100)
        self._ensure_file_exists()
        self.trim_entries()

    def _resolve_filepath(self, filepath):
        if os.path.isabs(filepath):
            return filepath

        if os.path.dirname(filepath) == "data":
            return os.path.join(DATA_ROOT, os.path.basename(filepath))

        return os.path.join(PROJECT_ROOT, filepath)

    def _ensure_file_exists(self):
        """Create the file if it does not exist (basic os usage)."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def read_all(self):
        with open(self.filepath, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def trim_entries(self):
        data = self.read_all()
        if len(data) <= self.max_entries:
            return

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data[-self.max_entries:], f, indent=4)

    def add_entry(self, entry):
        data = self.read_all()
        entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data.append(entry)
        data = data[-self.max_entries:]

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

class HistoryService(StorageService):
    def log_command(self, command, status, result):
        self.add_entry({"command": command, "status": status, "result": result})

class LoggerService(StorageService):
    def log_event(self, level, message, details=None):
        entry = {"level": level, "message": message}
        if details:
            entry["details"] = details
        self.add_entry(entry)
