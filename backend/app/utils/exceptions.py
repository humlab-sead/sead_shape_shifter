"""Custom exceptions for the backend application."""


class BaseAPIException(Exception):
    """Base exception for API-related errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(BaseAPIException):
    """Raised when a resource is not found."""

    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class BadRequestError(BaseAPIException):
    """Raised when request is malformed or invalid."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class ConflictError(BaseAPIException):
    """Raised when there is a conflict (e.g., duplicate resource)."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class InternalServerError(BaseAPIException):
    """Raised when an unexpected internal error occurs."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)
