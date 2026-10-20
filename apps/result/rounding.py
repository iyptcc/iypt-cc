from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property

from django.core.exceptions import ObjectDoesNotExist


def round_half_up(value, places=1):
    """Round a score for display, halves away from zero.

    All ranking arithmetic is done in full precision; rounding happens only
    at display time, halves up to match the official IYPT results. Score
    displays use this instead of floatformat so the rounding rule is explicit
    and independent of Django version and locale formatting (floatformat's
    rounding has changed across Django releases).
    """
    if value is None or value == "":
        return ""
    exp = Decimal(1).scaleb(-int(places))
    return Decimal(str(value)).quantize(exp, ROUND_HALF_UP)


class ScoreDisplay:
    """Decimal places for displayed scores, chosen per tournament.

    Legacy tournaments bake half-up rounding into the fight SP, so their pages
    show one decimal for SPs and totals and two for stage averages. With
    full-precision ranking (Tournament.ranking_unrounded_tsp) the pages show
    three decimals instead, so that the printed averages, fight scores and
    totals add up exactly: with 5 or 6 jurors per stage every average is a
    multiple of 1/8 or 1/10 and nothing is lost in three decimals.

    Templates get an instance as ``score_display`` from the context processor
    and use ``{{ t.sp|halfup:score_display.score }}``; the printer exposes the
    same object to the TeX templates. The tournament is looked up lazily, from
    the ``t_slug`` URL argument on public result pages or from the active
    tournament of the logged-in user elsewhere.
    """

    LEGACY = (1, 2)
    FULL_PRECISION = (3, 3)

    def __init__(self, tournament=None, request=None):
        self._tournament = tournament
        self._request = request

    @cached_property
    def tournament(self):
        if self._tournament is not None:
            return self._tournament
        request = self._request
        if request is None:
            return None
        match = getattr(request, "resolver_match", None)
        slug = match.kwargs.get("t_slug") if match else None
        if slug:
            from apps.tournament.models import Tournament

            return Tournament.objects.filter(slug=slug).first()
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            try:
                return user.profile.tournament
            except ObjectDoesNotExist:
                return None
        return None

    @cached_property
    def full_precision(self):
        trn = self.tournament
        return bool(trn is not None and trn.ranking_unrounded_tsp)

    @property
    def places(self):
        return self.FULL_PRECISION if self.full_precision else self.LEGACY

    @property
    def score(self):
        """Places for fight SPs and the total sum of points."""
        return self.places[0]

    @property
    def average(self):
        """Places for stage averages and the points derived from them."""
        return self.places[1]
