"""Domain error hierarchy.

These are raised anywhere in the backend and mapped to HTTP responses in a single
place (see ``api`` error handlers). Business/domain code raises these; it never
imports FastAPI or returns HTTP status codes itself.
"""

from __future__ import annotations


class MdiaError(Exception):
    """Base class for all MDIA domain errors."""


class ConfigError(MdiaError):
    """Application is misconfigured (e.g. a required env var is missing)."""


class NotFoundError(MdiaError):
    """A requested entity does not exist."""


class ValidationError(MdiaError):
    """Input failed a domain-level validation rule."""


class UnrecognisedFileError(ValidationError):
    """An uploaded file could not be read or matched to any source template."""
