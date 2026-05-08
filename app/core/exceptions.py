class ReceiptAssistantError(Exception):
    """Base exception for expected application errors."""


class FileStoreError(ReceiptAssistantError):
    """Base exception for upload storage errors."""


class UnsupportedFileTypeError(FileStoreError):
    """Raised when an uploaded file extension is not allowed."""


class UploadFileTooLargeError(FileStoreError):
    """Raised when an uploaded file exceeds the configured size limit."""


class InvalidSessionIdError(FileStoreError):
    """Raised when a session id cannot be safely used as a directory name."""


class CardStatementParserError(ReceiptAssistantError):
    """Base exception for card statement parser errors."""


class MissingRequiredColumnsError(CardStatementParserError):
    """Raised when a card statement does not include required standard columns."""
