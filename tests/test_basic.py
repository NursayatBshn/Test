import os
import sys
import tempfile

# Add the root folder to the import path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from abstractions.base_task import BaseTask
from services.rule_engine import RuleEngine
from tasks.core_tasks import OrganizeTask, file_generator

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

if __name__ == "__main__":
    test_file_generator()
    test_rule_engine_categories()
    test_rule_engine_uses_others_without_config()
    test_organize_reclassifies_files_from_others()
    print("All basic tests passed successfully!")
