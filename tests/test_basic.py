import os
import sys

# Add the root folder to the import path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from abstractions.base_task import BaseTask
from services.rule_engine import RuleEngine
from services.storage_services import HistoryService
from tasks.core_tasks import OrganizeTask, file_generator


def test_file_generator():
    os.makedirs("test_files", exist_ok=True)
    open("test_files/report.txt", "w").close()
    open("test_files/photo.png", "w").close()

    files = list(file_generator("test_files", ext=".txt"))

    assert len(files) == 1
    assert files[0].endswith("report.txt")

    os.remove("test_files/report.txt")
    os.remove("test_files/photo.png")
    os.rmdir("test_files")


def test_rule_engine_categories():
    rules = RuleEngine("configs/rules.json")

    assert rules.get_target_folder("photo.jpeg") == "Images"
    assert rules.get_target_folder("report.docx") == "Documents"
    assert rules.get_target_folder("backup.zip") == "Archives"


def test_base_task_inheritance():
    task = OrganizeTask()

    assert isinstance(task, BaseTask)
    assert task.name == "organize"


def test_organize_task_moves_files():
    os.makedirs("test_organize", exist_ok=True)
    open("test_organize/photo.jpg", "w").close()
    open("test_organize/report.pdf", "w").close()

    task = OrganizeTask()
    task.execute("--path test_organize")

    assert os.path.exists("test_organize/Images/photo.jpg")
    assert os.path.exists("test_organize/Documents/report.pdf")

    os.remove("test_organize/Images/photo.jpg")
    os.remove("test_organize/Documents/report.pdf")
    os.rmdir("test_organize/Images")
    os.rmdir("test_organize/Documents")
    os.rmdir("test_organize")


def test_history_service_limit():
    os.makedirs("test_storage", exist_ok=True)
    history = HistoryService("test_storage/history.json")

    for i in range(105):
        history.log_command(f"command-{i}", "SUCCESS", "ok")

    entries = history.read_all()

    assert len(entries) == 100
    assert entries[0]["command"] == "command-5"
    assert entries[-1]["command"] == "command-104"

    os.remove("test_storage/history.json")
    os.rmdir("test_storage")


if __name__ == "__main__":
    test_file_generator()
    test_rule_engine_categories()
    test_base_task_inheritance()
    test_organize_task_moves_files()
    test_history_service_limit()
    print("All basic tests passed successfully!")
