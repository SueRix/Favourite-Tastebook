from django.conf import settings


class VectorMatchPresenter:
    """
    What: Turns the raw Pinecone similarity carried on `vector_score` into the
          thermometer variables the card templates already understand.
    Where: Applied by RecipesDatabaseSearchPartialView to every search result set.
    Why: Cosine similarity between related texts lives in a narrow band, so a raw
         score would pin every card to the middle of the scale. Mapping a
         calibrated floor/ceiling window onto the full bar makes the difference
         readable while keeping two different searches comparable — normalising
         inside a single result set would not.
    """

    @staticmethod
    def _ratio(score: float) -> float:
        """
        Maps a raw similarity onto 0..1 using the configured calibration window,
        then bends it with VECTOR_SCORE_CURVE. The bend exists because the three
        anchor points the scale is tuned to (0.45 -> 0%, 0.48 -> 5%, 0.71 -> 100%)
        do not sit on a straight line: linearly, 0.48 would read as 12%.
        """
        floor = settings.VECTOR_SCORE_FLOOR
        span = settings.VECTOR_SCORE_CEILING - floor
        if span <= 0:
            # Misconfigured window: draw an empty bar instead of dividing by zero.
            return 0.0

        linear = min(max((score - floor) / span, 0.0), 1.0)

        curve = settings.VECTOR_SCORE_CURVE
        if curve <= 0:
            # A non-positive exponent would flatten every score to 100%.
            return linear

        return linear ** curve

    @classmethod
    def attach(cls, recipes):
        """
        What: Returns the recipes as a list, adding match-meter attributes to the
              ones that carry a vector score.
        Where: Called by the search partial view for every mode.
        Why: Keyword results have no similarity to show, so they pass through
             untouched and the template simply renders no thermometer. Keeping the
             check on the attribute rather than on the mode means any future engine
             that annotates `vector_score` gets the meter for free.
        """
        presented = list(recipes)

        for recipe in presented:
            score = getattr(recipe, "vector_score", None)
            if score is None:
                continue

            ratio = cls._ratio(score)
            recipe.match_percent = round(ratio * 100)
            # Same red -> green sweep as the ingredient-scoring thermometer.
            recipe.therm_fill_hue = round(ratio * 120)
            recipe.vector_score_label = f"{score:.2f}"
            recipe.show_match_meter = True

        return presented
