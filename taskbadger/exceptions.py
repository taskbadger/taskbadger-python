class ConfigurationError(Exception):
    def __init__(self, **kwargs):
        self.missing = [name for name, arg in kwargs.items() if arg is None]

    def __str__(self):
        return f"Missing configuration parameters: {', '.join(self.missing)}"


class TaskbadgerException(Exception):
    pass


class Unauthorized(TaskbadgerException):
    pass


class UnexpectedStatus(TaskbadgerException):
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content

        super().__init__(f"Unexpected status code: {status_code}")


class ServerError(UnexpectedStatus):
    pass
