import json
import os
from datetime import datetime

class StorageService:
    def __init__(self, filepath):
        self.filepath = filepath
        self._ensure_file_exists()

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

    def add_entry(self, entry):
        data = self.read_all()
        entry['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data.append(entry)
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