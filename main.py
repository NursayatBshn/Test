import sys
import readline
from services.command_processor import CommandProcessor

class CLICompleter:
    def __init__(self, commands):
        self.commands = commands

    def complete(self, text, state):
        """Method called by readline to find matches."""
        # Find all commands that start with the entered text.
        options = [cmd for cmd in self.commands if cmd.startswith(text)]
        
        if state < len(options):
            return options[state]
        else:
            return None

def print_banner():
    print("="*40)
    # Bump the version to v0.2 now that we have added extra features.
    print(" "*10 + "HyperCLI v0.2")
    print("="*40)
    print("Enter 'help' for the command list or 'exit' to quit.\n")

def main():
    print_banner()
    processor = CommandProcessor()
    
    # --- AUTOCOMPLETE SETUP (TAB) ---
    # Collect all commands from the processor and add 'exit'.
    available_commands = list(processor.tasks.keys()) + ["exit"]
    
    # Initialize our autocompleter.
    completer = CLICompleter(available_commands)
    readline.set_completer(completer.complete)
    
    # Tell readline to use TAB for autocompletion.
    readline.parse_and_bind('tab: complete')
    # --------------------------------------
    
    while True:
        try:
            user_input = input("HyperCLI > ")
            result = processor.process(user_input)
            
            if result == "exit":
                print("Shutting down HyperCLI. Goodbye!")
                break
                
        except KeyboardInterrupt:
            print("\nForced shutdown. Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"Critical error: {e}")

if __name__ == "__main__":
    main()
