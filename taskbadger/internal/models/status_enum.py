from enum import Enum


class StatusEnum(str, Enum):
    CANCELLED = "cancelled"
    ERROR = "error"
    PENDING = "pending"
    POST_PROCESSING = "post_processing"
    PRE_PROCESSING = "pre_processing"
    PROCESSING = "processing"
    STALE = "stale"
    SUCCESS = "success"

    def __str__(self) -> str:
        return str(self.value)
