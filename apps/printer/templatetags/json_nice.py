import decimal
import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


@register.filter
def jsonniceify(j):
    return json.dumps(j, sort_keys=True, indent=4, cls=DecimalEncoder)
