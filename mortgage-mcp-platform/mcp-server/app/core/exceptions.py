"""Application-specific exceptions."""

from __future__ import annotations


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "app_error") -> None:
        super().__init__(message)
        self.code = code


class ValidationAppError(AppError):
    """Input validation failure in domain layer."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error")


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="not_found")
