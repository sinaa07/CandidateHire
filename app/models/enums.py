from enum import Enum

class ResumeStatus(Enum):
    OK = "OK"
    FAILED = "FAILED"
    EMPTY = "EMPTY"
    DUPLICATE = "DUPLICATE"