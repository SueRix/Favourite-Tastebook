from __future__ import annotations

from .base import UserInputError, InternalError


class RecipeSelectionError(InternalError):
    code = "recipe_selection_error"
    public_message = "Recipe selection failed."


class InvalidScoreWeightsError(UserInputError):
    code = "invalid_score_weights"
    public_message = "Invalid score weights."

    def __init__(
        self,
        *,
        unknown_keys: list[str] | None = None,
        bad_key: str | None = None,
        reason: str | None = None,
    ):
        details = {"unknown_keys": unknown_keys, "bad_key": bad_key, "reason": reason}
        msg_parts: list[str] = []
        if unknown_keys:
            msg_parts.append(f"Unknown keys: {', '.join(unknown_keys)}")
        if bad_key:
            msg_parts.append(f"Bad key: {bad_key}")
        if reason:
            msg_parts.append(f"Reason: {reason}")
        super().__init__("; ".join(msg_parts) or self.public_message, details=details)
