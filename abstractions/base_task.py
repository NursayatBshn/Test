class BaseTask:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def execute(self, args):
        """Method that will be overridden in child classes (polymorphism)."""
        raise NotImplementedError("The execute() method must be overridden.")
