from decimal import ROUND_HALF_UP, Decimal


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
