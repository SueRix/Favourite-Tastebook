from recipe_manager.domain.enums import AgentRecipeSource
from recipe_manager.models import AgentPreference

#: What the assistant does for somebody who never opened the settings panel, and
#: for a guest, who has no row and never will. Kept here rather than read off the
#: model fields so a guest and a signed-in default answer identically.
DEFAULTS = {
    "use_tastes": True,
    "recipe_source": AgentRecipeSource.DATABASE.value,
    "autosave_drafts": False,
}


class AgentPreferenceSelector:
    """
    What: Reads one user's assistant settings, or the defaults when there is no
          row yet.
    Where: Called by the chat use case once per turn and by the tool endpoints
           that a setting restricts.
    Why: Reading must never write. A GET that quietly created a row would make
         merely opening the studio a database write, and would leave a row for
         every user who only ever looked at the page. The absent row IS the
         default state, so it is read as one.
    """

    @staticmethod
    def _is_authenticated(user) -> bool:
        return bool(user and getattr(user, "is_authenticated", False))

    @classmethod
    def for_user(cls, user) -> dict:
        """Returns {"use_tastes", "recipe_source", "autosave_drafts"}."""
        if not cls._is_authenticated(user):
            return dict(DEFAULTS)

        row = (
            AgentPreference.objects
            .filter(user=user)
            .values("use_tastes", "recipe_source", "autosave_drafts")
            .first()
        )
        if row is None:
            return dict(DEFAULTS)

        return {
            "use_tastes": row["use_tastes"],
            "recipe_source": row["recipe_source"],
            "autosave_drafts": row["autosave_drafts"],
        }
