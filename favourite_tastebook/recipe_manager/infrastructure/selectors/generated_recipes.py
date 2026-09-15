from recipe_manager.models import GeneratedRecipe


class GeneratedRecipeSelector:
    """
    Reads for the recipes the agent composed and the user kept. They live apart
    from the curated catalogue, so none of the Recipe selectors reach them.
    """

    @classmethod
    def list_for_user(cls, user, limit: int = 20):
        """
        The user's own creations, newest first, with ingredients prefetched.

        Bounded on purpose: the studio shows them as a sidebar of past work, not
        as a browsable archive, and every extra row is markup on a page that is
        already carrying a conversation.
        """
        if not user or not user.is_authenticated:
            return GeneratedRecipe.objects.none()

        return (
            GeneratedRecipe.objects
            .filter(user=user)
            .prefetch_related("ingredients__ingredient")
            .order_by("-created_at")[:limit]
        )
