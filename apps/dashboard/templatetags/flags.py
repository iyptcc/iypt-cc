from django import template
from django.utils.safestring import mark_safe

from apps.tournament.models import Origin

register = template.Library()

@register.filter
def flag(value):
    if type(value) != str:
        return "no str"
    if len(value) != 2:
        return "not iso alpha 2"
    if not value.isalpha():
        return "not alphpabet"

    value = value.upper()

    c1 = ord(value[0])-ord('A')+0x1F1E6
    c2 = ord(value[1])-ord('A')+0x1F1E6

    return mark_safe("&#%d;&#%d;"%(c1,c2))

@register.filter
def flag_url(origin):

    if origin.flag:
        return "/dashboard/flag/%s/%s"%(origin.tournament.slug, origin.slug)

    value = origin.alpha2iso
    if not value:
        return ""
    
    value = value.upper()

    c1 = ord(value[0])-ord('A')+0x1F1E6
    c2 = ord(value[1])-ord('A')+0x1F1E6

    #return "https://cdnjs.cloudflare.com/ajax/libs/twemoji/2.2.5/2/72x72/%x-%x.png"%(c1,c2)
    return "/static/flags/%x-%x.png"%(c1,c2)

@register.filter
def flag_image(origin):
    if type(origin) == Origin:

        return mark_safe('<div class="flag-container-72" data-toggle="tooltip" title="%s"><img class="flag-image-72" src="%s" /></div>'%(origin.name,flag_url(origin)))
