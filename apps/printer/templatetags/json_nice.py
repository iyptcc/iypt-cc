import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def jsonniceify(j):
    return json.dumps(j, sort_keys=True, indent = 4)
