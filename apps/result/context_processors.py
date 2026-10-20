from .rounding import ScoreDisplay


def score_display(request):
    """Expose the per-tournament display precision to every template."""
    return {"score_display": ScoreDisplay(request=request)}
