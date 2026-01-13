import re


class RecipeStepsParser:
    """
    Domain-level parser for x) steps, that placed in desc of db.
    """

    STEP_RE = re.compile(r"\s*\d+\)\s*")

    @classmethod
    def parse(cls, text):
        if not text:
            return []

        parts = cls.STEP_RE.split(text)
        return [p.strip() for p in parts if p.strip()]