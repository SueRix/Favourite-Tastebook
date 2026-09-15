from types import SimpleNamespace

from django.test import TestCase, override_settings

from recipe_manager.infrastructure.presentation.vector_match import VectorMatchPresenter


def _recipe(score=None):
    """Minimal stand-in: the presenter only ever touches attributes, not the ORM."""
    return SimpleNamespace(vector_score=score) if score is not None else SimpleNamespace()


@override_settings(VECTOR_SCORE_FLOOR=0.45, VECTOR_SCORE_CEILING=0.71, VECTOR_SCORE_CURVE=1.4)
class VectorMatchPresenterTests(TestCase):
    """Covers the calibration window that turns raw cosine similarity into a bar."""

    def _percent(self, score):
        [presented] = VectorMatchPresenter.attach([_recipe(score)])
        return presented.match_percent

    def test_hits_the_three_calibration_anchors(self):
        # The scale is tuned to these points; they do not sit on a straight line,
        # which is the whole reason VECTOR_SCORE_CURVE exists.
        for score, expected in ((0.45, 0), (0.48, 5), (0.71, 100)):
            with self.subTest(score=score):
                self.assertEqual(self._percent(score), expected)

    def test_curve_pulls_the_weak_tail_below_the_straight_line(self):
        # Linearly 0.48 would read as 12%; the curve must rate it lower, not higher.
        with override_settings(VECTOR_SCORE_CURVE=1.0):
            self.assertEqual(self._percent(0.48), 12)
        self.assertEqual(self._percent(0.48), 5)

    def test_percent_rises_monotonically_with_score(self):
        percents = [self._percent(s) for s in (0.46, 0.50, 0.55, 0.60, 0.65, 0.70)]
        self.assertEqual(percents, sorted(percents))
        self.assertEqual(len(set(percents)), len(percents))

    def test_hue_follows_percent_on_the_red_to_green_sweep(self):
        [presented] = VectorMatchPresenter.attach([_recipe(0.71)])
        self.assertEqual(presented.match_percent, 100)
        self.assertEqual(presented.therm_fill_hue, 120)

    def test_score_at_or_below_floor_is_clamped_to_zero(self):
        for score in (0.45, 0.20, -1.0):
            with self.subTest(score=score):
                self.assertEqual(self._percent(score), 0)

    def test_score_above_ceiling_is_clamped_to_full(self):
        self.assertEqual(self._percent(0.99), 100)

    def test_raw_score_is_kept_for_the_tooltip(self):
        [presented] = VectorMatchPresenter.attach([_recipe(0.6428)])
        self.assertEqual(presented.vector_score_label, "0.64")

    def test_results_without_a_score_pass_through_untouched(self):
        # Keyword results have no similarity: no meter must be drawn for them.
        [presented] = VectorMatchPresenter.attach([_recipe()])
        self.assertFalse(hasattr(presented, "show_match_meter"))
        self.assertFalse(hasattr(presented, "match_percent"))

    @override_settings(VECTOR_SCORE_FLOOR=0.71, VECTOR_SCORE_CEILING=0.71)
    def test_degenerate_window_draws_an_empty_bar_instead_of_dividing_by_zero(self):
        self.assertEqual(self._percent(0.9), 0)

    @override_settings(VECTOR_SCORE_CURVE=0)
    def test_non_positive_curve_falls_back_to_linear(self):
        # x ** 0 == 1 would paint every card as a perfect match.
        self.assertEqual(self._percent(0.58), 50)
