import os
import shutil
import re
import json
import sys
import termios
import tty

from abstractions.base_task import BaseTask
from utils.decorators import log_execution
from services.result_formatter import ResultFormatter
from services.rule_engine import RuleEngine
from services.storage_services import DATA_ROOT
from services.app_config import AppConfig

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
        super().__init__(
            "search",
            "Searches for files by filters",
            usage="search --path <folder> [--ext <extension>]",
            examples=[
                "search --path /home/user/Downloads",
                "search --path /home/user/Downloads --ext .pdf"
            ]
        )

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
        super().__init__(
            "organize",
            "Sorts files in the specified folder using configs/rules.json",
            usage="organize --path <folder>",
            examples=["organize --path /home/user/Downloads"]
        )
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
        super().__init__(
            "cleanup",
            "Deletes empty folders in the specified directory",
            usage="cleanup --path <folder>",
            examples=["cleanup --path /home/user/Downloads"]
        )

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
        super().__init__(
            "help",
            "Shows the command list or details for one command",
            usage="help [command]",
            examples=["help", "help logs", "help organize"]
        )
        self.tasks_dict = tasks_dict

    def execute(self, args):
        args = args.strip().lower()
        if args in self.tasks_dict:
            task = self.tasks_dict[args]
            lines = [
                f"Help for command '{task.name}':",
                f"  Description: {task.description}"
            ]
            if task.usage:
                lines.append(f"  Usage: {task.usage}")
            if task.examples:
                lines.append("  Examples:")
                for example in task.examples:
                    lines.append(f"    {example}")
            return "\n".join(lines)
        elif args:
            raise ValueError(f"Command '{args}' not found. Enter 'help' for the command list.")

        lines = ["Available commands:"]
        for name, task in self.tasks_dict.items():
            lines.append(f"  {name} - {task.description}")
        return "\n".join(lines)

class HistoryTask(BaseTask):
    def __init__(self):
        self.display_limit = AppConfig.get("history", "display_limit", 100)
        super().__init__(
            "history",
            f"Shows up to the last {self.display_limit} executed commands",
            usage="history",
            examples=["history"]
        )
        self.history_file = os.path.join(DATA_ROOT, "history.json")

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

        recent_data = data[-self.display_limit:]
        headers = ["Time", "Command", "Status"]
        rows = [[item.get('timestamp', '-'), item.get('command', '-'), item.get('status', '-')] for item in recent_data]

        return "Recent actions:\n" + ResultFormatter.format_table(headers, rows)

class LogsTask(BaseTask):
    def __init__(self):
        self.page_size = AppConfig.get("logs", "page_size", 10)
        self.message_width = AppConfig.get("logs", "message_width", 30)
        self.details_width = AppConfig.get("logs", "details_width", 70)
        self.min_pager_width = AppConfig.get("logs", "min_pager_width", 60)
        self.default_pager_width = AppConfig.get("logs", "default_pager_width", 100)
        self.max_separator_width = AppConfig.get("logs", "max_separator_width", 120)
        super().__init__(
            "logs",
            f"Shows system logs, {self.page_size} entries per page",
            usage="logs [--page <number>] [--full] [--paper|--pager]",
            examples=[
                "logs",
                "logs --page 2",
                "logs --full",
                "logs --full --page 2",
                "logs --paper"
            ]
        )
        self.logs_file = os.path.join(DATA_ROOT, "logs.json")

    def execute(self, args):
        args = args.strip()
        if not os.path.exists(self.logs_file):
            return "Logs are empty."

        data = self._load_logs()
        if not data:
            return "Logs are empty."

        if "--pager" in args or "--paper" in args:
            return self._run_pager(data)

        page = self._parse_page(args)
        if "--full" in args:
            return self._format_full_page(data, page)

        return self._format_page(data, page)

    def _load_logs(self):
        with open(self.logs_file, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                raise ValueError("Error reading logs.")

    def _parse_page(self, args):
        page_match = re.search(r'--page\s+(\d+)', args)
        if not page_match:
            return 1

        return max(1, int(page_match.group(1)))

    def _format_page(self, data, page):
        total_pages = max(1, (len(data) + self.page_size - 1) // self.page_size)
        page = min(page, total_pages)
        page_data = self._get_page_data(data, page)

        headers = ["Level", "Time", "Message", "Details"]
        rows = [
            [
                item.get('level', '-'),
                item.get('timestamp', '-'),
                self._truncate(item.get('message', '-'), self.message_width),
                self._format_details(item.get('details', {}))
            ]
            for item in page_data
        ]

        return (
            f"System journal (page {page}/{total_pages}, {len(page_data)} of {len(data)} logs):\n"
            + ResultFormatter.format_table(headers, rows)
        )

    def _format_full_page(self, data, page):
        total_pages = max(1, (len(data) + self.page_size - 1) // self.page_size)
        page = min(page, total_pages)
        page_data = self._get_page_data(data, page)
        lines = [f"System journal details (page {page}/{total_pages}, {len(page_data)} of {len(data)} logs):"]

        for index, item in enumerate(page_data, start=1):
            details = json.dumps(item.get("details", {}), ensure_ascii=False, indent=2)
            lines.extend([
                "",
                f"{index}. [{item.get('level', '-')}] {item.get('timestamp', '-')}",
                f"Message: {item.get('message', '-')}",
                "Details:",
                details
            ])

        return "\n".join(lines)

    def _get_page_data(self, data, page):
        end = len(data) - ((page - 1) * self.page_size)
        start = max(0, end - self.page_size)
        return data[start:end]

    def _format_details(self, details):
        details_text = json.dumps(details or {}, ensure_ascii=False)
        return self._truncate(details_text, self.details_width)

    def _truncate(self, text, width):
        text = str(text)
        if len(text) <= width:
            return text

        return text[:width - 3] + "..."

    def _run_pager(self, data):
        if not sys.stdin.isatty():
            return self._format_page(data, 1)

        page = 1
        total_pages = max(1, (len(data) + self.page_size - 1) // self.page_size)
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            tty.setraw(sys.stdin.fileno())
            sys.stdout.write("\033[?1049h")
            while True:
                sys.stdout.write("\033[2J\033[H")
                sys.stdout.write(self._format_pager_page(data, page))
                sys.stdout.write("\r\n\r\nLeft: newer | Right: older | q: quit")
                sys.stdout.flush()

                key = self._read_key()
                if key in ("q", "Q"):
                    break
                if key == "RIGHT" and page < total_pages:
                    page += 1
                elif key == "LEFT" and page > 1:
                    page -= 1
        finally:
            sys.stdout.write("\033[?1049l")
            sys.stdout.flush()
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        return "Closed logs pager."

    def _format_pager_page(self, data, page):
        total_pages = max(1, (len(data) + self.page_size - 1) // self.page_size)
        page = min(page, total_pages)
        page_data = self._get_page_data(data, page)
        width = max(self.min_pager_width, shutil.get_terminal_size((self.default_pager_width, 24)).columns)
        details_width = max(20, width - 12)
        separator = "-" * min(width, self.max_separator_width)
        lines = [
            f"System journal page {page}/{total_pages} ({len(page_data)} of {len(data)} logs)",
            separator
        ]

        for index, item in enumerate(page_data, start=1):
            details = json.dumps(item.get("details", {}), ensure_ascii=False)
            lines.extend([
                f"{index}. [{item.get('level', '-')}] {item.get('timestamp', '-')}",
                f"   {self._truncate(item.get('message', '-'), details_width)}",
                f"   details: {self._truncate(details, details_width)}",
                ""
            ])

        return "\r\n".join(lines)

    def _read_key(self):
        char = sys.stdin.read(1)
        if char != "\x1b":
            return char

        sequence = sys.stdin.read(2)
        if sequence == "[C":
            return "RIGHT"
        if sequence == "[D":
            return "LEFT"

        return char

    def _clear_screen(self):
        print("\033[2J\033[H", end="")

class StatsTask(BaseTask):
    def __init__(self):
        super().__init__(
            "stats",
            "Shows statistics and a chart of file types",
            usage="stats --path <folder>",
            examples=["stats --path /home/user/Downloads"]
        )
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
