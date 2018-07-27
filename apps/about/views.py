import codecs
import os

import markdown
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.html import mark_safe
from django.views import View
from markdown.extensions.tables import TableExtension

# Create your views here.

def info(request):

    return render(request, "about/info.html")

def tos(request):

    return render(request, "about/tos.html")

def help(request):

    path = os.path.join(os.path.dirname(__file__),"pages","index.md")

    if request.path[:7] == "/about/":
        dir = request.path[7:]

        unsafe_path = os.path.join(os.path.dirname(__file__),"pages",dir)

        if unsafe_path.startswith(os.path.join(os.path.dirname(__file__),"pages")):
            safe_path = unsafe_path
            if os.path.isfile(safe_path):
                path = safe_path

    input_file = codecs.open(path, mode="r", encoding="utf-8")
    text = input_file.read()

    html = markdown.markdown(text, extensions=[TableExtension()])

    return render(request, "about/help.html", context={"file": mark_safe(html)})
