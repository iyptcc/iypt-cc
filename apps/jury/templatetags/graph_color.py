import hashlib

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def rgbFromName(key):
    h = hashlib.md5(("trashh%s"%key).encode('ascii'))
    digest = h.hexdigest()
    n = int(digest, 16)
    print(n)
    r = n%256
    rr = n//256
    g = rr%256
    gg = rr//256
    b = gg%256
    return mark_safe('%d, %d, %d'%(r,g,b))
