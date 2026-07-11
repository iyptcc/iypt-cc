from django import template

from apps.result.rounding import round_half_up

register = template.Library()


@register.filter
def halfup(value, places=1):
    """Display a full-precision score rounded half up, e.g. {{ t.tsp|halfup:1 }}."""
    return round_half_up(value, places)
