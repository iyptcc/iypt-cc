import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase

from apps.result.rounding import round_half_up
from apps.result.templatetags.rounding import halfup
from apps.result.utils import _fightresult, _ranking


def make_round(publish_ranking, fights, unrounded_tsp=False):
    """Mock Round object exposing round.publish_ranking and round.fight_set.all()."""
    round_obj = MagicMock()
    round_obj.publish_ranking = publish_ranking
    round_obj.fight_set.all.return_value = fights
    round_obj.tournament.ranking_unrounded_tsp = unrounded_tsp
    return round_obj


class RankingTiesTests(SimpleTestCase):

    @patch("apps.result.utils._fightresult")
    def test_ranking_matches_expected_grades(self, mock_fightresult):
        fight = MagicMock()
        round1 = make_round(True, [fight])

        mock_fightresult.return_value = {
            'room': 'A',
            'round': 1,
            'result': [{'pk': 25, 'won': True, 'name': 'Austria', 'sp': Decimal('19.9'), 'slug': 'austria'},
                       {'pk': 4, 'won': False, 'name': 'Bahrain', 'sp': Decimal('12.8'), 'slug': 'bahrain'},
                       {'pk': 21, 'won': False, 'name': 'Albania', 'sp': Decimal('0.0'), 'slug': 'albania'}
                    ]
        }

        grades = _ranking([round1], use_cache=False)

        expected = [
            [
                {
                    "rank": 1,
                    "pk": 25,
                    "team": "Austria",
                    "slug": "austria",
                    "tsp": Decimal("19.9"),
                    "won": 1,
                    "sp": [(Decimal("19.9"), True, "A")],
                    "all_won": True,
                },
                {
                    "rank": 2,
                    "pk": 4,
                    "team": "Bahrain",
                    "slug": "bahrain",
                    "tsp": Decimal("12.8"),
                    "won": 0,
                    "sp": [(Decimal("12.8"), False, "A")],
                    "all_won": False,
                },
                {
                    "rank": 3,
                    "pk": 21,
                    "team": "Albania",
                    "slug": "albania",
                    "tsp": Decimal("0.0"),
                    "won": 0,
                    "sp": [(Decimal("0.0"), False, "A")],
                    "all_won": False,
                },
            ]
        ]

        self.assertEqual(grades, expected)

    @patch("apps.result.utils._fightresult")
    def test_same_tsp_different_won_breaks_tie_by_won(self, mock_fightresult):
        fight_r1 = MagicMock()
        fight_r2 = MagicMock()

        round1 = make_round(True, [fight_r1])
        round2 = make_round(True, [fight_r2])

        def side_effect(fight, use_cache=True):
            if fight is fight_r1:
                # Both teams win round 1 with equal sp -> tied rank 1
                return {
                    "room": "A",
                    "round": 1,
                    "result": [
                        {"pk": 25, "won": True, "name": "Austria", "sp": Decimal("15.0"), "slug": "austria"},
                        {"pk": 4, "won": True, "name": "Bahrain", "sp": Decimal("15.0"), "slug": "bahrain"},
                    ],
                }
            # Round 2: Bahrain wins again, Austria loses. tsp ends up equal.
            return {
                "room": "A",
                "round": 2,
                "result": [
                    {"pk": 25, "won": False, "name": "Austria", "sp": Decimal("5.0"), "slug": "austria"},
                    {"pk": 4, "won": True, "name": "Bahrain", "sp": Decimal("5.0"), "slug": "bahrain"},
                ],
            }

        mock_fightresult.side_effect = side_effect

        grades = _ranking([round1, round2], use_cache=False)

        #print("grades", json.dumps(grades, indent=2, default=str))
        final = {t["pk"]: t for t in grades[-1]}

        # Same total tsp for both teams
        self.assertEqual(final[25]["tsp"], Decimal("20.0"))
        self.assertEqual(final[4]["tsp"], Decimal("20.0"))

        # But different won counts
        self.assertEqual(final[25]["won"], 1)  # won round 1 only
        self.assertEqual(final[4]["won"], 2)  # won both rounds

        # Bahrain (more wins) ranks above Austria despite equal tsp
        self.assertEqual(final[4]["rank"], 1)
        self.assertEqual(final[25]["rank"], 2)

        # all_won reflects perfect record only
        self.assertFalse(final[25]["all_won"])  # lost round 2
        self.assertTrue(final[4]["all_won"])  # won every fight

        # rank_diff: both tied rank 1 after round 1.
        # Bahrain stays at rank 1 -> diff = 1 - 1 = 0
        self.assertEqual(final[4]["rank_diff"], 0)
        # Austria drops from rank 1 to rank 2 -> diff = 1 - 2 = -1
        self.assertEqual(final[25]["rank_diff"], -1)


class RankingTspAccumulationTests(SimpleTestCase):
    """Legacy tsp sums the (rounded) fight SPs; in full-precision mode the
    fight results already carry unrounded SPs, so the tsp is their exact sum
    and is only rounded for display by the result.rounding filters."""

    def _rank(self, sps_r1, sps_r2, unrounded_tsp):
        fight_r1 = MagicMock()
        fight_r2 = MagicMock()

        round1 = make_round(True, [fight_r1], unrounded_tsp)
        round2 = make_round(True, [fight_r2], unrounded_tsp)

        def side_effect(fight, use_cache=True):
            sps = sps_r1 if fight is fight_r1 else sps_r2
            return {
                "room": "A",
                "round": 1 if fight is fight_r1 else 2,
                "result": [
                    {"pk": 25, "won": True, "name": "Austria",
                     "sp": sps[0], "slug": "austria"},
                    {"pk": 4, "won": False, "name": "Bahrain",
                     "sp": sps[1], "slug": "bahrain"},
                ],
            }

        with patch("apps.result.utils._fightresult", side_effect=side_effect):
            grades = _ranking([round1, round2], use_cache=False)
        return {t["pk"]: t for t in grades[-1]}

    def test_legacy_tsp_sums_rounded_sps(self):
        final = self._rank(
            [Decimal("19.3"), Decimal("10.0")],
            [Decimal("20.3"), Decimal("10.0")],
            unrounded_tsp=False,
        )
        self.assertEqual(final[25]["tsp"], Decimal("39.6"))
        self.assertEqual(final[4]["tsp"], Decimal("20.0"))

    def test_full_precision_tsp_is_exact_sum(self):
        final = self._rank(
            [Decimal("19.25"), Decimal("10.0")],
            [Decimal("20.25"), Decimal("10.0")],
            unrounded_tsp=True,
        )
        # exact, never rounded in the calculation
        self.assertEqual(final[25]["tsp"], Decimal("39.50"))
        self.assertEqual(final[4]["tsp"], Decimal("20.0"))


def make_attendance(pk, name, grade_average):
    attendance = MagicMock()
    attendance.team.pk = pk
    attendance.team_id = pk
    attendance.team.origin.name = name
    attendance.team.origin.slug = name.lower()
    attendance.grade_average = grade_average
    return attendance


class FightSpRoundingTests(SimpleTestCase):
    """Legacy fight SPs bake in half-up rounding; in full-precision mode the
    SP stays exact and is rounded only for display. (Official IYPT pages round
    halves up in every consistently-generated cell and in all totals; their
    winner cells on exact halves are a known inconsistency of the iypt.ch
    generator that no rounding rule reproduces.)"""

    def _fightresult(self, unrounded_tsp):
        fight = MagicMock()
        fight.pk = 1
        fight.round.review_phase = False
        fight.round.tournament.ranking_unrounded_tsp = unrounded_tsp
        fight.round.order = 1
        fight.room.name = "A"

        stage = MagicMock()
        # 6.75 * factor 3 = 20.25, exactly on the rounding boundary
        stage.rep_attendance_grades = make_attendance(25, "Austria", Decimal("6.75"))
        stage.opp_attendance_grades = make_attendance(4, "Bahrain", Decimal("5"))
        fight.stage_set.all.return_value = [stage]

        with patch("apps.result.utils._report_factor", return_value=3.0), patch(
            "apps.result.utils._opposition_factor", return_value=2.0
        ), patch("apps.result.utils._att_penalty", return_value=0):
            context = _fightresult(fight, use_cache=False)
        return {t["pk"]: t for t in context["result"]}

    def test_legacy_sp_rounds_half_up(self):
        result = self._fightresult(unrounded_tsp=False)
        self.assertEqual(result[25]["sp"], Decimal("20.3"))
        self.assertEqual(result[4]["sp"], Decimal("10.0"))

    def test_full_precision_sp_stays_exact(self):
        result = self._fightresult(unrounded_tsp=True)
        self.assertEqual(result[25]["sp"], Decimal("20.25"))
        self.assertEqual(result[4]["sp"], Decimal("10.0"))


class DisplayRoundingTests(SimpleTestCase):
    """Score displays round halves up via result.rounding, an explicit rule
    independent of Django's floatformat (whose rounding has changed across
    Django releases) and of locale formatting."""

    def test_sp_display_rounds_half_up(self):
        self.assertEqual(round_half_up(Decimal("20.25"), 1), Decimal("20.3"))
        self.assertEqual(round_half_up(Decimal("46.25"), 1), Decimal("46.3"))

    def test_weighted_average_display_rounds_half_up(self):
        self.assertEqual(round_half_up(Decimal("11.625"), 2), Decimal("11.63"))

    def test_non_halves_unchanged(self):
        self.assertEqual(round_half_up(Decimal("20.24"), 1), Decimal("20.2"))
        self.assertEqual(round_half_up(Decimal("20.26"), 1), Decimal("20.3"))

    def test_none_renders_empty(self):
        self.assertEqual(round_half_up(None, 1), "")

    def test_template_filter(self):
        self.assertEqual(halfup(Decimal("20.25"), 1), Decimal("20.3"))
