class ConfigurationError(Exception):
    def __init__(self, **kwargs):
        self.missing = [name for name, arg in kwargs.items() if arg is None]

    def __str__(self):
        return f"Missing configuration parameters: {', '.join(self.missing)}"
