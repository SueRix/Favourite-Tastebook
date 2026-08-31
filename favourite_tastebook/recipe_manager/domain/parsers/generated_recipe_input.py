from recipe_manager.domain.enums import Importance, Units
from recipe_manager.domain.parsers.agent_input import AgentInput

# Vocabularies a composed recipe may use. Kept next to the parser rather than in
# the tool layer because both front doors — the agent and the studio page —
# validate against exactly the same set.
ALLOWED_UNITS = {value: value for value in Units.values}
ALLOWED_IMPORTANCE = {value: value for value in Importance.values}

MAX_TITLE = 255
MAX_CUISINE = 100
MAX_INGREDIENT_NAME = 100

# A dish nobody can cook within a day is a hallucinated number, not a slow roast.
MAX_COOK_TIME = 1440
DEFAULT_COOK_TIME = 30


class GeneratedRecipeInput:
    """
    What: Reads the JSON shape of a composed recipe — the same one the agent
          proposes and the studio page saves.
    Where: Used by AgentToolsUseCase (propose / save tools) and by the studio
           save view.
    Why: The page lets a person edit the agent's draft before keeping it, which
         means there are two ways for a recipe to reach the database. If each
         parsed its own payload they would drift, and the editable form would
         eventually accept something the tool would have refused — including,
         eventually, an ingredient off the taboo list. One parser makes that
         impossible by construction.
    """

    @staticmethod
    def ingredient_line(line: dict) -> dict:
        """One {name, amount, unit, importance} entry."""
        return {
            # Ingredient.name is stored lowercase, so match on the same form.
            "name": AgentInput.text(line, "name", max_length=MAX_INGREDIENT_NAME).lower(),
            "amount": AgentInput.amount(line, "amount"),
            "unit": AgentInput.choice(line, "unit", ALLOWED_UNITS, Units.GRAM),
            "importance": AgentInput.choice(
                line, "importance", ALLOWED_IMPORTANCE, Importance.REQUIRED
            ),
        }

    @classmethod
    def parse(cls, payload: dict) -> dict:
        """
        Returns the keyword arguments SaveGeneratedRecipeUseCase expects.
        Raises AgentPayloadError for anything the contract does not allow.
        """
        return {
            "title": AgentInput.text(payload, "title", max_length=MAX_TITLE),
            "cuisine": AgentInput.text(
                payload, "cuisine", required=False, max_length=MAX_CUISINE
            ),
            "cook_time": AgentInput.integer(
                payload,
                "cook_time_minutes",
                default=DEFAULT_COOK_TIME,
                minimum=1,
                maximum=MAX_COOK_TIME,
            ),
            "steps": AgentInput.paragraph_list(payload, "steps"),
            "ingredient_lines": [
                cls.ingredient_line(line)
                for line in AgentInput.object_list(payload, "ingredients")
            ],
        }
