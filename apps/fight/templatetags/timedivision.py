from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def tominsec(v):

    return "%d:%02d" % (v // 60, v % 60)
