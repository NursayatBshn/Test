import os
import shutil
import re
import json

from abstractions.base_task import BaseTask
from utils.decorators import log_execution
from services.result_formatter import ResultFormatter
from services.rule_engine import RuleEngine

def file_generator(path, ext=None):
    """Generator for lazy directory traversal (for search)."""
    for root, _, files in os.walk(path):
        for file in files:
            if ext:
                if file.endswith(ext):
                    yield os.path.join(root, file)
            else:
                yield os.path.join(root, file)

class SearchTask(BaseTask):
    def __init__(self):
        super().__init__("search", "Searches for files by filters (--path, --ext)")

    @log_execution
    def execute(self, args):
        path = "."
        ext = None
        
        path_match = re.search(r'--path\s+([^\s]+)', args)
        ext_match = re.search(r'--ext\s+([^\s]+)', args)
        
        if path_match: path = path_match.group(1)
        if ext_match: ext = ext_match.group(1)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Path {path} does not exist.")

        # Get the file list through the generator.
        found_files = list(file_generator(path, ext))
        
        if not found_files:
            return "No files found."

        headers = ["NAME", "SIZE", "DATE"]
        rows = []

        for file_path in found_files:
            try:
                stats = os.stat(file_path)
                name = os.path.basename(file_path)
                
                # Format the size (MB).
                size_mb = f"{stats.st_size / (1024 * 1024):.2f}MB"
                
                # Format the modification date.
                from datetime import datetime
                date = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d')
                
                rows.append([name, size_mb, date])
            except Exception:
                continue # Skip files that cannot be accessed.

        # Use our formatter to create a table.
        return "Search results:\n" + ResultFormatter.format_table(headers, rows)

class OrganizeTask(BaseTask):
    def __init__(self, logger=None):
        super().__init__("organize", "Sorts files in the specified folder (--path)")
        self.rule_engine = RuleEngine(os.path.join("configs", "rules.json"))
        self.logger = logger

    @log_execution
    def execute(self, args):
        path_match = re.search(r'--path\s+([^\s]+)', args)
        if not path_match:
            raise ValueError("Specify a folder with --path")
        
        path = path_match.group(1)
        if not os.path.exists(path):
            raise FileNotFoundError("The specified folder does not exist.")

        created_folders = set()
        moved_count = 0
        skipped_count = 0
        failed_count = 0

        self._log("INFO", "Organization started", {
            "path": path,
            "rules_file": self.rule_engine.rules_file,
            "rules_source": self.rule_engine.rules_source,
            "rules_count": len(self.rule_engine.rules)
        })

        for file_path in self._iter_organizable_files(path):
            if self._is_logger_file(file_path):
                skipped_count += 1
                self._log("DEBUG", "Logger file skipped", {"file": file_path})
                continue

            rule = self.rule_engine.get_matching_rule(file_path)
            folder_name = rule.get("target") if rule else "Others"
            target_dir = os.path.join(path, folder_name)
            target_path = os.path.join(target_dir, os.path.basename(file_path))

            if os.path.abspath(file_path) == os.path.abspath(target_path):
                skipped_count += 1
                self._log("DEBUG", "File already in target folder", {
                    "file": file_path,
                    "target_folder": folder_name
                })
                continue
            
            if target_dir not in created_folders:
                os.makedirs(target_dir, exist_ok=True)
                created_folders.add(target_dir)
            
            try:
                final_target_path = self._get_available_target_path(target_path)
                shutil.move(file_path, final_target_path)
                moved_count += 1
                self._log("INFO", "File moved", {
                    "source": file_path,
                    "target": final_target_path,
                    "target_folder": folder_name,
                    "matched_extension": rule.get("extension") if rule else None,
                    "used_default_folder": rule is None
                })
            except Exception as e:
                failed_count += 1
                self._log("ERROR", "File move failed", {
                    "source": file_path,
                    "target": target_path,
                    "target_folder": folder_name,
                    "error": str(e)
                })

        self._log("INFO", "Organization finished", {
            "path": path,
            "moved": moved_count,
            "skipped": skipped_count,
            "failed": failed_count
        })

        return f"Organization complete. Files moved: {moved_count}. Skipped: {skipped_count}. Failed: {failed_count}."

    def _iter_organizable_files(self, path):
        managed_folders = self.rule_engine.get_target_folders()
        managed_folders.add("Others")

        for item in os.listdir(path):
            item_path = os.path.join(path, item)

            if os.path.isfile(item_path) and os.path.splitext(item_path)[1]:
                yield item_path
            elif os.path.isdir(item_path) and item in managed_folders:
                for root, _, files in os.walk(item_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.splitext(file_path)[1]:
                            yield file_path

    def _get_available_target_path(self, target_path):
        if not os.path.exists(target_path):
            return target_path

        base, ext = os.path.splitext(target_path)
        counter = 1

        while True:
            candidate = f"{base}_{counter}{ext}"
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    def _log(self, level, message, details):
        if self.logger:
            self.logger.log_event(level, message, details)

    def _is_logger_file(self, file_path):
        if not self.logger:
            return False

        return os.path.abspath(file_path) == os.path.abspath(self.logger.filepath)

class CleanupTask(BaseTask):
    def __init__(self):
        super().__init__("cleanup", "Deletes empty folders in the specified directory (--path)")

    @log_execution
    def execute(self, args):
        path_match = re.search(r'--path\s+([^\s]+)', args)
        if not path_match:
            raise ValueError("Specify a directory with --path")
        
        target_dir = path_match.group(1)
        if not os.path.exists(target_dir):
            raise FileNotFoundError("The specified directory does not exist.")

        removed_count = 0
        # Traverse bottom-up to safely remove nested empty folders.
        for root, dirs, files in os.walk(target_dir, topdown=False):
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        removed_count += 1
                except Exception:
                    pass

        return f"Cleanup complete. Empty folders removed: {removed_count}."

class HelpTask(BaseTask):
    def __init__(self, tasks_dict):
        super().__init__("help", "Shows the command list (use 'help <command>' for details)")
        self.tasks_dict = tasks_dict

    def execute(self, args):
        args = args.strip().lower()
        if args in self.tasks_dict:
            task = self.tasks_dict[args]
            return f"Help for command '{task.name}':\n  Description: {task.description}"
        elif args:
            raise ValueError(f"Command '{args}' not found. Enter 'help' for the command list.")

        lines = ["Available commands:"]
        for name, task in self.tasks_dict.items():
            lines.append(f"  {name} - {task.description}")
        return "\n".join(lines)

class HistoryTask(BaseTask):
    def __init__(self):
        super().__init__("history", "Shows the history of executed commands")
        self.history_file = os.path.join("data", "history.json")

    def execute(self, args):
        if not os.path.exists(self.history_file):
            return "History is empty."

        with open(self.history_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                raise ValueError("Error reading history (file is corrupted).")

        if not data:
            return "History is empty."

        recent_data = data[-10:]
        headers = ["Time", "Command", "Status"]
        rows = [[item.get('timestamp', '-'), item.get('command', '-'), item.get('status', '-')] for item in recent_data]

        return "Recent actions:\n" + ResultFormatter.format_table(headers, rows)

class LogsTask(BaseTask):
    def __init__(self):
        super().__init__("logs", "Shows system logs")
        self.logs_file = os.path.join("data", "logs.json")

    def execute(self, args):
        if not os.path.exists(self.logs_file):
            return "Logs are empty."

        with open(self.logs_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                raise ValueError("Error reading logs.")

        recent_data = data[-10:]
        headers = ["Level", "Time", "Message", "Details"]
        rows = [
            [
                item.get('level', '-'),
                item.get('timestamp', '-'),
                item.get('message', '-'),
                json.dumps(item.get('details', {}), ensure_ascii=False)
            ]
            for item in recent_data
        ]

        return "System journal:\n" + ResultFormatter.format_table(headers, rows)

class StatsTask(BaseTask):
    def __init__(self):
        super().__init__("stats", "Shows statistics and a chart of file types (--path)")
        self.rule_engine = RuleEngine(os.path.join("configs", "rules.json"))

    @log_execution
    def execute(self, args):
        path_match = re.search(r'--path\s+([^\s]+)', args)
        if not path_match:
            raise ValueError("Specify a directory with --path")
        
        target_dir = path_match.group(1)
        if not os.path.exists(target_dir):
            raise FileNotFoundError("The specified directory does not exist.")

        category_sizes = {}
        total_size = 0

        # Scan files and count sizes.
        for root, _, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if not os.path.isfile(file_path):
                    continue
                
                try:
                    size = os.path.getsize(file_path)
                    total_size += size
                    category = self.rule_engine.get_target_folder(file_path)
                    category_sizes[category] = category_sizes.get(category, 0) + size
                except Exception:
                    pass # Ignore files that cannot be accessed.

        if total_size == 0:
            return "The directory is empty or contains only zero-size files."

        # Build the ASCII chart.
        lines = [f"Statistics for: {target_dir}", "-" * 50]
        
        # Sort categories by size (largest to smallest).
        sorted_categories = sorted(category_sizes.items(), key=lambda item: item[1], reverse=True)
        
        for cat, size in sorted_categories:
            percent = (size / total_size) * 100
            bar_length = int(percent / 5)  # 20 characters maximum (100% / 5).
            bar = "█" * bar_length + "-" * (20 - bar_length)
            size_mb = size / (1024 * 1024)
            lines.append(f"{cat.ljust(12)} [{bar}] {percent:>5.1f}% ({size_mb:.2f} MB)")

        lines.append("-" * 50)
        lines.append(f"Total size: {total_size / (1024 * 1024):.2f} MB")
        
        return "\n".join(lines)
