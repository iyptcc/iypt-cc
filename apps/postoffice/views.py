from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, View

from .default_context import default_template_context
from .forms import TemplateForm, TemplateNewForm
from .models import Template, TemplateVersion
from .utils import render_template

# Create your views here.

class ListTemplates(ListView):

    template_name = "postoffice/templates.html"

    def get_queryset(self):

        return Template.objects.filter(tournament=self.request.user.profile.tournament)

class AddTemplate(View):

    def get(self, request):
        form = TemplateNewForm(request.user.profile.tournament)

        return render(request, "printer/template_new.html", context={"form":form})

    def post(self, request):
        form = TemplateNewForm(request.user.profile.tournament, request.POST)
        if form.is_valid():

            tpl = Template.objects.create(tournament= request.user.profile.tournament,
                                          name=form.cleaned_data["name"],
                                          type=form.cleaned_data["type"])
            TemplateVersion.objects.create(template=tpl, author= request.user.profile, src="")

            return redirect("postoffice:templates")

        return render(request,"printer/template_new.html", context={"form":form})

class EditTemplate(View):

    def get(self, request, id):

        template = get_object_or_404(Template, id=id, tournament=request.user.profile.tournament)

        form = TemplateForm(template)

        if template.type in default_template_context:
            context = default_template_context[template.type]
        else:
            context={}

        return render(request, "printer/template_edit.html", context={"form":form,"context":context})

    def post(self, request, id):

        trn = request.user.profile.tournament
        template = get_object_or_404(Template, id=id, tournament=trn)

        form = TemplateForm(template, request.POST)

        if form.is_valid():

            if 'type' in form.changed_data:
                template.type = form.cleaned_data["type"]
                template.save()

            if 'tname' in form.changed_data:
                template.name = form.cleaned_data["tname"]
                template.save()

            if 'src' in form.changed_data or 'subject' in form.changed_data:
                TemplateVersion.objects.create(template=template, author=request.user.profile, src=form.cleaned_data["src"], subject=form.cleaned_data["subject"])

            if "_save" in request.POST:
                return redirect("postoffice:templates")

            if "_source" in request.POST:

                if form.cleaned_data['type'] in default_template_context:
                    context = default_template_context[template.type]
                else:
                    context = {}

                srcs = render_template(template.id,context)

                emails = []
                for src in srcs:
                    emails.append({"email":"test@email.com","subject":src[0],"body":src[1]})

                return render(request,"postoffice/source.html",context={'srcs':emails})


        return render(request, "printer/template_edit.html", context={"form": form})

class ListTemplateVersions(ListView):

    template_name = "printer/template_versions.html"

    def get_queryset(self):

        template = get_object_or_404(Template, tournament=self.request.user.profile.tournament, id=self.kwargs["id"])

        return template.templateversion_set.all()
