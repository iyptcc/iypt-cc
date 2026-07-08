import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase

from apps.result.utils import _ranking  # adjust import path to where _ranking lives


def make_round(publish_ranking, fights):
    """Mock Round object exposing round.publish_ranking and round.fight_set.all()."""
    round_obj = MagicMock()
    round_obj.publish_ranking = publish_ranking
    round_obj.fight_set.all.return_value = fights
    return round_obj


class RankingTiesTests(SimpleTestCase):

    @patch("apps.result.utils._fightresult")
    def test_ranking_matches_expected_grades(self, mock_fightresult):
        fight = MagicMock()
        round1 = MagicMock()
        round1.publish_ranking = True
        round1.fight_set.all.return_value = [fight]

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

        round1 = MagicMock()
        round1.publish_ranking = True
        round1.fight_set.all.return_value = [fight_r1]

        round2 = MagicMock()
        round2.publish_ranking = True
        round2.fight_set.all.return_value = [fight_r2]

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