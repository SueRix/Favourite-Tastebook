
class ProfileError(Exception):
    """Base class for profile-related errors."""


class ProfileNotFound(ProfileError):
    """Requested profile does not exist."""


class InvalidFormData(ProfileError):
    """Submitted form data is invalid."""

    def __init__(self, user_errors=None, profile_errors=None, message="Invalid form data"):
        super().__init__(message)
        self.user_errors = user_errors or {}
        self.profile_errors = profile_errors or {}
