from enum import Enum


class StatusEnum(str, Enum):
    PENDING = "pending"
    PRE_PROCESSING = "pre_processing"
    PROCESSING = "processing"
    POST_PROCESSING = "post_processing"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    STALE = "stale"

    def __str__(self) -> str:
        return str(self.value)
