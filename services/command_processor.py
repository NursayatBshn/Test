from tasks.core_tasks import SearchTask, OrganizeTask, CleanupTask, StatsTask, HelpTask, HistoryTask, LogsTask  
from services.storage_services import HistoryService, LoggerService
import os

class CommandProcessor:
    def __init__(self):
        self.history = HistoryService(os.path.join("data", "history.json"))
        self.logger = LoggerService(os.path.join("data", "logs.json"))
        
        # Initialize tasks (composition).
        self.tasks = {
            "search": SearchTask(),
            "organize": OrganizeTask(self.logger),
            "cleanup": CleanupTask(),
            "stats": StatsTask(),
            "history": HistoryTask(),
            "logs": LogsTask()
        }
        # Pass the task dictionary to HelpTask (association).
        self.tasks["help"] = HelpTask(self.tasks)

    def process(self, input_string):
        if not input_string.strip():
            return
            
        parts = input_string.split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command_name == "exit":
            return "exit"

        task = self.tasks.get(command_name)
        
        if task:
            try:
                result = task.execute(args)
                print(f"\n{result}\n")
                self.history.log_command(input_string, "SUCCESS", "Executed successfully")
                self.logger.log_event("INFO", f"Command executed: {command_name}")
            except Exception as e:
                error_msg = f"Execution error: {str(e)}"
                print(f"\n{error_msg}\n")
                self.history.log_command(input_string, "FAILED", error_msg)
                self.logger.log_event("ERROR", error_msg)
        else:
            print("\nUnknown command. Enter 'help' for the command list.\n")
            self.logger.log_event("WARNING", f"Unknown command: {command_name}")
