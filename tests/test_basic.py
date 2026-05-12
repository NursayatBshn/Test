import json
import os
import sys
import tempfile

# Add the root folder to the import path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from abstractions.base_task import BaseTask
from services.storage_services import HistoryService, LoggerService, DATA_ROOT
from services.rule_engine import RuleEngine
from tasks.core_tasks import HelpTask, HistoryTask, LogsTask, OrganizeTask, file_generator

def test_file_generator():
    """Test the custom iterator/generator."""
    # Create a test structure.
    os.makedirs("test_dir", exist_ok=True)
    with open("test_dir/test1.txt", "w") as f: f.write("1")
    with open("test_dir/test2.png", "w") as f: f.write("2")
    
    files = list(file_generator("test_dir", ext=".txt"))
    
    # Assertions
    assert len(files) == 1, "The generator should find only one .txt file"
    assert "test1.txt" in files[0], "The wrong file was found"
    
    # Cleanup.
    os.remove("test_dir/test1.txt")
    os.remove("test_dir/test2.png")
    os.rmdir("test_dir")

def test_rule_engine_categories():
    rules = RuleEngine("configs/rules.json")

    assert rules.get_target_folder("photo.jpeg") == "Images"
    assert rules.get_target_folder("report.docx") == "Documents"
    assert rules.get_target_folder("backup.tar.gz") == "Archives"

def test_rule_engine_uses_others_without_config():
    rules = RuleEngine("missing-rules.json")

    assert rules.get_target_folder("photo.jpeg") == "Others"
    assert rules.get_target_folder("report.docx") == "Others"
    assert rules.get_target_folder("backup.zip") == "Others"

def test_organize_reclassifies_files_from_others():
    with tempfile.TemporaryDirectory() as tmpdir:
        others_dir = os.path.join(tmpdir, "Others")
        os.makedirs(others_dir)

        open(os.path.join(others_dir, "photo.jpeg"), "w").close()
        open(os.path.join(others_dir, "report.docx"), "w").close()
        open(os.path.join(others_dir, "backup.zip"), "w").close()

        OrganizeTask().execute(f"--path {tmpdir}")

        assert os.path.exists(os.path.join(tmpdir, "Images", "photo.jpeg"))
        assert os.path.exists(os.path.join(tmpdir, "Documents", "report.docx"))
        assert os.path.exists(os.path.join(tmpdir, "Archives", "backup.zip"))

def test_storage_services_keep_last_100_entries():
    with tempfile.TemporaryDirectory() as tmpdir:
        history = HistoryService(os.path.join(tmpdir, "history.json"))
        logs = LoggerService(os.path.join(tmpdir, "logs.json"))

        for index in range(105):
            history.log_command(f"command-{index}", "SUCCESS", "ok")
            logs.log_event("INFO", f"event-{index}")

        history_entries = history.read_all()
        log_entries = logs.read_all()

        assert len(history_entries) == 100
        assert len(log_entries) == 100
        assert history_entries[0]["command"] == "command-5"
        assert log_entries[0]["message"] == "event-5"

def test_history_shows_last_100_and_logs_show_pages_of_10():
    history_file = os.path.join(DATA_ROOT, "history.json")
    logs_file = os.path.join(DATA_ROOT, "logs.json")
    original_history = None
    original_logs = None

    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            original_history = f.read()
    if os.path.exists(logs_file):
        with open(logs_file, "r", encoding="utf-8") as f:
            original_logs = f.read()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            os.makedirs(os.path.dirname(history_file), exist_ok=True)

            history_entries = [
                {"timestamp": "-", "command": f"command-{index}", "status": "SUCCESS"}
                for index in range(105)
            ]
            log_entries = [
                {"timestamp": "-", "level": "INFO", "message": f"event-{index}"}
                for index in range(105)
            ]

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_entries, f)
            with open(logs_file, "w", encoding="utf-8") as f:
                json.dump(log_entries, f)

            history_output = HistoryTask().execute("")
            logs_output = LogsTask().execute("")
            logs_page_2_output = LogsTask().execute("--page 2")
            logs_full_output = LogsTask().execute("--full")
            logs_paper_output = LogsTask().execute("--paper")

            assert "command-0" not in history_output
            assert "command-5" in history_output
            assert "event-94" not in logs_output
            assert "event-95" in logs_output
            assert "event-104" in logs_output
            assert "event-84" not in logs_page_2_output
            assert "event-85" in logs_page_2_output
            assert "event-94" in logs_page_2_output
            assert "System journal details" in logs_full_output
            assert "Message: event-104" in logs_full_output
            assert "System journal (page 1/" in logs_paper_output
    finally:
        if original_history is None:
            os.remove(history_file)
        else:
            with open(history_file, "w", encoding="utf-8") as f:
                f.write(original_history)

        if original_logs is None:
            os.remove(logs_file)
        else:
            with open(logs_file, "w", encoding="utf-8") as f:
                f.write(original_logs)

def test_help_shows_updated_logs_usage():
    logs = LogsTask()
    help_task = HelpTask({"logs": logs})

    output = help_task.execute("logs")

    assert "logs [--page <number>] [--full] [--paper|--pager]" in output
    assert "logs --full --page 2" in output
    assert "logs --paper" in output

if __name__ == "__main__":
    test_file_generator()
    test_rule_engine_categories()
    test_rule_engine_uses_others_without_config()
    test_organize_reclassifies_files_from_others()
    test_storage_services_keep_last_100_entries()
    test_history_shows_last_100_and_logs_show_pages_of_10()
    test_help_shows_updated_logs_usage()
    print("All basic tests passed successfully!")
