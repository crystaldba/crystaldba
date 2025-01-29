"""Custom exceptions for CrystalDBA."""

__all__ = ["APIError", "ConfigurationError", "CrystalDBAError", "ProfileError", "ProfileNotFoundError"]


class CrystalDBAError(Exception):
    """Base exception for all CrystalDBA errors."""

    pass


class ProfileError(CrystalDBAError):
    """Base exception for profile-related errors."""

    pass


class ProfileNotFoundError(ProfileError):
    """Raised when a profile cannot be found."""

    pass


class ConfigurationError(CrystalDBAError):
    """Raised when there's an error in configuration."""

    pass


class APIError(CrystalDBAError):
    """Raised when there's an error in API communication."""

    pass
