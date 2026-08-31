import json
from decimal import Decimal, InvalidOperation

from recipe_manager.domain.exceptions import AgentPayloadError

# Hard ceilings, independent of what the caller asks for. The values below are
# not user preferences: they bound how much text one tool call can push into the
# model's context window and how much work a single LLM turn can cost us.
MAX_TEXT_LENGTH = 300
MAX_LIST_ITEMS = 30
MAX_ITEM_LENGTH = 60
# Cooking steps are prose, not labels, so they get their own, larger budget.
MAX_STEPS = 20
MAX_STEP_LENGTH = 600
# Mirrors RecipeIngredient.amount: DecimalField(max_digits=6, decimal_places=2).
MIN_AMOUNT = Decimal("0.01")
MAX_AMOUNT = Decimal("9999.99")


class AgentInput:
    """
    What: Type-safe readers for the JSON body of a tool call.
    Where: Used by AgentToolsUseCase before any of the arguments reach a selector.
    Why: Every value here was invented by an LLM, so it is untrusted input in the
         strictest sense — wrong types, absurd sizes and empty strings are the
         normal case, not the exception. Failing with AgentPayloadError turns them
         into a 400 the agent can retry, instead of a 500 in the middle of a chat.
    """

    @staticmethod
    def text(payload: dict, key: str, required: bool = True, default: str = "",
             max_length: int = MAX_TEXT_LENGTH) -> str:
        value = payload.get(key, default)

        if value is None:
            value = default
        if not isinstance(value, str):
            raise AgentPayloadError(f"'{key}' must be a string.")

        cleaned = value.strip()
        if required and not cleaned:
            raise AgentPayloadError(f"'{key}' is required.")

        # Truncate rather than reject: a chatty model padding the query with a
        # whole sentence should still get results, not an error it cannot fix.
        return cleaned[:max_length]

    @staticmethod
    def integer(payload: dict, key: str, default: int, minimum: int = 1, maximum: int = None) -> int:
        value = payload.get(key)
        if value is None or value == "":
            return default

        # Models routinely send numbers as strings; accept both, reject the rest.
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise AgentPayloadError(f"'{key}' must be an integer.") from exc

        if number < minimum:
            number = minimum
        if maximum is not None and number > maximum:
            number = maximum
        return number

    @staticmethod
    def required_id(payload: dict, key: str) -> int:
        value = payload.get(key)
        if value is None or value == "":
            raise AgentPayloadError(f"'{key}' is required.")

        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise AgentPayloadError(f"'{key}' must be an integer id.") from exc

        if number < 1:
            raise AgentPayloadError(f"'{key}' must be a positive id.")
        return number

    @staticmethod
    def string_list(payload: dict, key: str, required: bool = True,
                    max_items: int = MAX_LIST_ITEMS, max_item_length: int = MAX_ITEM_LENGTH) -> list[str]:
        value = payload.get(key)

        # A single-item list is frequently emitted as a bare string, and several
        # items as one comma-separated string; both are cheaper to accept here
        # than to fight in the tool description.
        if isinstance(value, str):
            value = [part for part in value.split(",")]
        if value is None:
            value = []
        if not isinstance(value, list):
            raise AgentPayloadError(f"'{key}' must be a list of strings.")

        cleaned = []
        for item in value[:max_items]:
            if not isinstance(item, (str, int, float)):
                raise AgentPayloadError(f"'{key}' must contain only strings.")
            text = str(item).strip().lower()[:max_item_length]
            if text and text not in cleaned:
                cleaned.append(text)

        if required and not cleaned:
            raise AgentPayloadError(f"'{key}' must contain at least one value.")
        return cleaned

    @staticmethod
    def choice(payload: dict, key: str, allowed: dict, default: str) -> str:
        value = payload.get(key)
        if value is None or value == "":
            return default
        if not isinstance(value, str):
            raise AgentPayloadError(f"'{key}' must be a string.")

        normalised = value.strip().lower()
        if normalised not in allowed:
            raise AgentPayloadError(
                f"'{key}' must be one of: {', '.join(sorted(allowed))}."
            )
        return normalised

    @staticmethod
    def paragraph_list(payload: dict, key: str, max_items: int = MAX_STEPS,
                       max_item_length: int = MAX_STEP_LENGTH) -> list[str]:
        """
        Ordered prose, unlike string_list: cooking steps keep their case, their
        order and their duplicates ("simmer 10 minutes" can legitimately appear
        twice), so none of the normalisation done for ingredient names applies.
        """
        value = payload.get(key)

        # A model that ignored the array in the schema and sent one blob of text
        # still means the steps in order; splitting is cheaper than a retry.
        if isinstance(value, str):
            value = value.splitlines()
        if value is None:
            value = []
        if not isinstance(value, list):
            raise AgentPayloadError(f"'{key}' must be a list of strings.")

        cleaned = []
        for item in value[:max_items]:
            if not isinstance(item, str):
                raise AgentPayloadError(f"'{key}' must contain only strings.")
            text = item.strip()[:max_item_length]
            if text:
                cleaned.append(text)

        if not cleaned:
            raise AgentPayloadError(f"'{key}' must contain at least one step.")
        return cleaned

    @staticmethod
    def object_list(payload: dict, key: str, max_items: int = MAX_LIST_ITEMS) -> list[dict]:
        """A list of JSON objects — used for the ingredient lines of a recipe."""
        value = payload.get(key)

        # Tool arguments cross the agent as text, and a nested array is exactly
        # what a model most often hands over still serialised. Parsing it here
        # turns the single most likely failure of the save tool into a success.
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise AgentPayloadError(f"'{key}' is not valid JSON.") from exc

        if value is None:
            value = []
        if not isinstance(value, list):
            raise AgentPayloadError(f"'{key}' must be a list of objects.")

        items = []
        for item in value[:max_items]:
            if not isinstance(item, dict):
                raise AgentPayloadError(f"'{key}' must contain objects, not plain values.")
            items.append(item)

        if not items:
            raise AgentPayloadError(f"'{key}' must contain at least one entry.")
        return items

    @staticmethod
    def amount(payload: dict, key: str, default: str = "1") -> Decimal:
        """
        A quantity bounded by what the column can physically store. Out-of-range
        values are clamped rather than rejected: "300 g of salt" is a bad recipe,
        but it is not a reason to fail a save the user already asked for.
        """
        value = payload.get(key, default)
        if value is None or value == "":
            value = default

        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise AgentPayloadError(f"'{key}' must be a number.") from exc

        if not number.is_finite():
            raise AgentPayloadError(f"'{key}' must be a finite number.")

        number = min(max(number, MIN_AMOUNT), MAX_AMOUNT)
        return number.quantize(Decimal("0.01"))
