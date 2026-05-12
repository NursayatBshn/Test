class BaseTask:
    def __init__(self, name, description, usage=None, examples=None):
        self.name = name
        self.description = description
        self.usage = usage
        self.examples = examples or []

    def execute(self, args):
        """Method that will be overridden in child classes (polymorphism)."""
        raise NotImplementedError("The execute() method must be overridden.")
