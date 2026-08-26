from django.views.generic import TemplateView

from recipe_manager.application.use_cases.search_recipes import SearchRecipesUseCase


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
        What: Builds the template context with the cleaned keyword and matching recipes queryset.
        Where: Invoked by Django's TemplateView during HTMX GET handling.
        Why: Delegates all business logic to the use case so the view stays a thin presenter.
        """
        ctx = super().get_context_data(**kwargs)
        keyword = self.request.GET.get("keyword", "")
        mode = self.request.GET.get("mode", "keyword")
        ctx["keyword"] = keyword
        ctx["mode"] = mode
        ctx["recipes"] = SearchRecipesUseCase.execute(
            keyword,
            mode=mode,
            user=self.request.user,
        )
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
