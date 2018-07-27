from django import forms
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from formtools.preview import FormPreview

from apps.dashboard.forms import ModelDeleteListField

from .models import Pdf


@method_decorator(login_required, name='__call__')
class PdfsPreview(FormPreview):

    form_template = "printer/list.html"
    preview_template = "dashboard/previewObjsDelete.html"

    def parse_params(self, request):

        pdfs = ModelDeleteListField(queryset=Pdf.objects.filter(tournament=request.user.profile.tournament))

        self.form = type("PdfsForm", (forms.Form,), {'pdfs':pdfs})

    def process_preview(self, request, form, context):

        def format_callback(obj):
            return '%s: %s' % (capfirst(obj._meta.verbose_name), obj)


        ps = form.cleaned_data['pdfs']
        collector = NestedObjects(using='default')  # or specific database
        collector.collect(ps)
        to_delete = collector.nested(format_callback)

        context['objs']=to_delete

    @method_decorator(permission_required('printer.delete_pdf'))
    def done(self, request, cleaned_data):

        ps = cleaned_data['pdfs']

        ps.delete()

        return redirect('printer:list')
