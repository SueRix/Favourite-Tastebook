from abc import ABC, abstractmethod

from django.db.models import QuerySet


class RecipeSelectionStrategy(ABC):
    """
    Abstract contract for a single, self-contained way of selecting recipes
    from a text keyword.

    Every concrete strategy (classic SQL keyword search, vector similarity via
    Pinecone, ...) is fully independent: it takes the same input and returns the
    same output type, so the application layer can swap them behind one switch
    without any other layer knowing which engine actually ran.
    """

    @abstractmethod
    def select(self, keyword: str, user=None) -> QuerySet:
        """
        Args:
            keyword (str): Raw search text as typed by the user.
            user: The requesting user (or AnonymousUser); may be used for
                  personalised filtering, ignored by strategies that don't need it.

        Returns:
            QuerySet[Recipe]: Matching recipes. May be empty (Recipe.objects.none()),
                              but must always be a Recipe QuerySet so the presentation
                              layer stays identical across strategies.
        """
        raise NotImplementedError