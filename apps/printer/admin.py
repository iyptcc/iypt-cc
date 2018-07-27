from django.contrib import admin

from .models import DefaultTemplate, Pdf, PdfTag, Template, TemplateVersion

# Register your models here.

admin.site.register(Pdf)
admin.site.register(Template)
admin.site.register(TemplateVersion)
admin.site.register(PdfTag)
admin.site.register(DefaultTemplate)
