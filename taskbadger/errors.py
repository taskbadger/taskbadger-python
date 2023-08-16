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
