"""Custom exception classes for the application."""


class ContenZavodError(Exception):
    """Base exception for all application errors."""

    pass


class DuplicateContentError(ContenZavodError):
    """Raised when trying to create content that already exists (by hash)."""

    pass


class ProviderError(ContenZavodError):
    """Raised when an AI provider encounters an error."""

    pass


class PublishError(ContenZavodError):
    """Raised when publishing to a channel fails."""

    pass


class RateLimitError(ContenZavodError):
    """Raised when API rate limits are hit."""

    pass
