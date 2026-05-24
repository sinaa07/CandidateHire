from enum import Enum


class ResumeStatus(Enum):
    OK = "OK"
    FAILED = "FAILED"
    EMPTY = "EMPTY"
    DUPLICATE = "DUPLICATE"


class ExtractionState(Enum):
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    OCR_PENDING = "OCR_PENDING"
    OCR_DONE = "OCR_DONE"
    OCR_FAILED = "OCR_FAILED"