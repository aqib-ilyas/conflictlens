"""
Custom exceptions for VIEWS API.
"""


class ViewsAPIError(Exception):
    """Base exception for VIEWS API errors."""
    pass


class DataNotFoundError(ViewsAPIError):
    """Raised when requested data is not found."""
    pass


class ValidationError(ViewsAPIError):
    """Raised when input validation fails."""
    pass


class DataLoadError(ViewsAPIError):
    """Raised when data loading fails."""
    pass


class ConfigurationError(ViewsAPIError):
    """Raised when configuration is invalid."""
    pass