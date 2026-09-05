import logging

from django.views.generic import TemplateView

from recipe_manager.application.use_cases.search_recipes import SearchRecipesUseCase
from recipe_manager.domain.exceptions import VectorSearchException
from recipe_manager.infrastructure.presentation.vector_match import VectorMatchPresenter

logger = logging.getLogger(__name__)

# Badge shown above semantic result sets. Presentation only: the keyword mode
# is deliberately absent, it has no similarity to label.
MODE_LABELS = {
    "vector": "Semantic",
    "ingredient": "Ingredient",
}


class RecipesDatabaseView(TemplateView):
    """
    What: Renders the main "Recipes Database" page shell.
    Where: Mounted at the `recipes_database` URL; entry point for the database browsing experience.
    Why: Provides the static container that hosts the HTMX-driven search partial.
    """
    template_name = "main/recipes_database.html"


class RecipesDatabaseSearchPartialView(TemplateView):
    """
    What: Handles HTMX GET requests for the keyword search and renders only the results partial.
    Where: Targeted by the search input on the Recipes Database page via hx-get.
    Why: Keeps the page responsive by swapping only the results fragment instead of full reloads.
    """
    template_name = "partials/recipes_search_results.html"

    def get_context_data(self, **kwargs):
        """
        What: Builds the template context with the cleaned keyword, the selection mode and the matching recipes.
        Where: Invoked by Django's TemplateView during HTMX GET handling.
        Why: Delegates all business logic to the use case so the view stays a thin presenter.
        """
        ctx = super().get_context_data(**kwargs)
        keyword = self.request.GET.get("keyword", "")
        mode = self.request.GET.get("mode", "keyword")
        ctx["keyword"] = keyword
        ctx["mode"] = mode
        ctx["mode_label"] = MODE_LABELS.get(mode)
        ctx["search_error"] = None

        try:
            # The presenter is a no-op for engines that carry no similarity,
            # so the keyword path is unaffected.
            ctx["recipes"] = VectorMatchPresenter.attach(
                SearchRecipesUseCase.execute(
                    keyword,
                    mode=mode,
                    user=self.request.user,
                )
            )
        except VectorSearchException as exc:
            # HTMX swaps whatever comes back straight into #rdb-results, so an
            # unhandled 500 would render Django's error page inside the results
            # area. Degrade to an empty result set plus a readable message.
            # Catching the base class keeps future subclasses covered.
            logger.warning("Vector search failed: %s", exc)
            ctx["recipes"] = []
            # The instance message carries transport details (webhook URL,
            # HTTP body); show the class-level, user-facing text instead and
            # keep the diagnostics in the logs.
            ctx["search_error"] = type(exc).message

        return ctx


class RecipesDatabaseCardPartialView(TemplateView):
    """
    What: Handles HTMX GET requests to render a single recipe's detail modal on the Recipes Database page.
    Where: Triggered when a user clicks a recipe card produced by RecipesDatabaseSearchPartialView.
    Why: Reuses the existing detailed card layout so the database page provides the same recipe experience as the home page.
    """
    template_name = "partials/recipe_database_card_modal.html"

    def get_context_data(self, **kwargs):
        """
        What: Resolves the requested recipe and exposes it under the `featured` key expected by the modal template.
        Where: Invoked by Django's TemplateView during HTMX GET handling for the card detail endpoint.
        Why: Keeps the view a thin presenter while delegating data assembly to SearchRecipesUseCase.
        """
        ctx = super().get_context_data(**kwargs)
        ctx["featured"] = SearchRecipesUseCase.get_card_detail(
            kwargs.get("recipe_id"),
            self.request.user,
        )
        return ctx
