from django import template
from unidecode import unidecode as ud

register = template.Library()


@register.filter
def unidecode(string):
    return ud(string)
