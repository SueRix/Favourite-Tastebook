from recipe_manager.domain.enums import AgentRecipeSource
from recipe_manager.domain.exceptions import AgentPayloadError
from recipe_manager.infrastructure.selectors import AgentPreferenceSelector
from recipe_manager.models import AgentPreference

#: The switches the settings panel owns, and nothing else. Anything outside this
#: set is ignored rather than refused: the panel and this list are versioned
#: apart, and a stale tab sending one extra key should not lose the whole edit.
BOOLEAN_FIELDS = ("use_tastes", "autosave_drafts")


class AgentSettingsUseCase:
    """
    What: Reads and writes how the assistant should behave for one user.
    Where: Behind the gear button in the Recipe Studio; the values it stores are
           then read by the chat use case and by the tool endpoints.
    Why: The panel sends whatever the person touched, which is usually one
         switch out of three. A partial update is therefore the normal case, not
         an edge case — every field absent from the payload keeps the value it
         had, so two switches flipped in two tabs cannot undo each other.

    Validation is strict on the values and lenient on the keys. A value that is
    not a boolean, or a source that is not one of the two we know, is a bug or a
    forged request and is refused; an unknown key is simply not ours.
    """

    @staticmethod
    def read(user) -> dict:
        return AgentPreferenceSelector.for_user(user)

    @staticmethod
    def _boolean(payload: dict, field: str):
        value = payload[field]
        if isinstance(value, bool):
            return value
        # Checkboxes reach us as JSON from the studio, but a form post is a
        # plausible second caller and sends strings.
        if isinstance(value, str) and value.lower() in {"true", "false", "1", "0", "on", "off"}:
            return value.lower() in {"true", "1", "on"}
        raise AgentPayloadError(f"'{field}' must be true or false.")

    @staticmethod
    def _source(payload: dict):
        value = payload["recipe_source"]
        if value not in AgentRecipeSource.values:
            allowed = ", ".join(AgentRecipeSource.values)
            raise AgentPayloadError(f"'recipe_source' must be one of: {allowed}.")
        return value

    @classmethod
    def update(cls, user, payload: dict) -> dict:
        """
        Applies the fields present in `payload` and returns the settings as they
        stand afterwards. Raises AgentPayloadError on a value we cannot store.
        """
        if not isinstance(payload, dict):
            raise AgentPayloadError("Settings must be a JSON object.")

        changes = {}
        for field in BOOLEAN_FIELDS:
            if field in payload:
                changes[field] = cls._boolean(payload, field)
        if "recipe_source" in payload:
            changes["recipe_source"] = cls._source(payload)

        if not changes:
            raise AgentPayloadError("No known setting was given.")

        # The row is created on the first change and only then: a user who never
        # opens this panel never gets one, and the selector reads the defaults.
        AgentPreference.objects.update_or_create(user=user, defaults=changes)

        return AgentPreferenceSelector.for_user(user)
