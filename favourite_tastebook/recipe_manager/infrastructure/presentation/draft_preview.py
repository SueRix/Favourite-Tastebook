from types import SimpleNamespace

from recipe_manager.domain.enums import Importance

# The same three buckets, in the same order, that FeaturedRecipePresenter builds
# for a catalogue recipe. A preview that grouped its ingredients differently
# would stop being a preview of the same card.
INGREDIENT_GROUPS = (
    ("Required", Importance.REQUIRED),
    ("Secondary", Importance.SECONDARY),
    ("Optional", Importance.OPTIONAL),
)


class DraftPreviewPresenter:
    """
    What: Dresses a draft — a recipe that exists only in the editor on screen —
          in the attributes the recipe card template reads off a Recipe row.
    Where: Used by RecipeStudioPreviewView, which renders the very same partial
           the database page renders for a stored recipe.
    Why: "Show me what this will look like" has exactly one honest answer: the
         real card, from the real template. Anything else is a second layout to
         keep in step with the first, and it would drift the day somebody
         restyles one of them. So instead of a preview template there is a
         preview presenter, and the template cannot tell the difference.

    `is_preview` is the one thing it says about itself. The card carries like,
    dislike and save buttons that address a recipe by id, and a draft has no id
    to give them — it may never be saved at all. The template hides them on that
    flag rather than rendering controls that would act on some other recipe.
    """

    @staticmethod
    def _group(title: str, importance: str, lines: list[dict]) -> dict:
        return {
            "title": title,
            "items": [
                {
                    "name": line["name"],
                    "amount": line["amount"],
                    "unit": line["unit"],
                    "importance": line["importance"],
                }
                for line in lines
                if line["importance"] == importance
            ],
        }

    @classmethod
    def build(cls, *, title: str, cuisine: str, cook_time: int, steps: list[str],
              ingredient_lines: list[dict], image_url: str = "") -> SimpleNamespace:
        """
        Takes GeneratedRecipeInput's keyword arguments — the draft as it was
        typed, already length-checked — and returns the object the card reads.

        Nothing here is looked up in the database on purpose. An ingredient the
        catalogue does not know is refused by the save and said so on its row in
        the editor; the preview's job is to show the draft as it stands, not to
        become a second, quieter place where that verdict is delivered.
        """
        return SimpleNamespace(
            is_preview=True,
            title=title,
            cook_time=cook_time,
            cuisine_label=cuisine or "General",
            # Falsy means "no photo available", which is what the card already
            # prints for a catalogue recipe that has no image.
            poster_url=image_url,
            steps=steps,
            # Empty groups are dropped rather than passed on empty: a draft with
            # no ingredients yet should get the card's own "No ingredients data"
            # line, and that line only appears when the whole list is empty.
            ingredient_groups=[
                group
                for group in (
                    cls._group(group_title, importance, ingredient_lines)
                    for group_title, importance in INGREDIENT_GROUPS
                )
                if group["items"]
            ],
        )
