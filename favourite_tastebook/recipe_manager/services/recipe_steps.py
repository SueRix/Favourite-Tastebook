#ARCH-TODO: this file, as a parser, must be in domain layer.
import re
from typing import List


class RecipeStepsService:
    """
    Responsible only for parsing and preparing recipe step text.
    """

    _STEP_RE = re.compile(r"\s*\d+\)\s*")

    @classmethod
    def split(cls, text: str | None) -> List[str]:
        if not text:
            return []

        parts = cls._STEP_RE.split(text)
        return [p.strip() for p in parts if p.strip()]
