from __future__ import absolute_import, unicode_literals

import traceback

from celery import current_task, shared_task, states
from django.conf import settings
from django.core.files.base import ContentFile

from apps.printer.models import Pdf, Template

from .utils import render_template


@shared_task
def render_to_pdf_local(template_id, pdf_id, context=None):


    pdf_obj = Pdf.objects.get(id=pdf_id)

    if not context:
        context={}
    try:
        src = render_template(template_id, context)
    except Exception as e:
        pdf_obj.status = Pdf.ERROR
        pdf_obj.save()
        return {"err":repr(e),"context":context}

    import tempfile
    from subprocess import Popen, PIPE
    import os

    env = os.environ.copy()
    env["TEXMFHOME"] = os.path.join(settings.BASE_DIR, 'tex', 'texmf')
    # env["OPENTYPEFONTS"] = ':' + os.path.join(settings.BASE_DIR, 'cc', 'static', 'ssp', 'OTF') + ':'
    # env["TTFONTS"] = ':' + os.path.join(settings.BASE_DIR, 'cc', 'static', 'ssp', 'TTF') + ':'
    # env["TEXMFVAR"] = os.path.join(settings.BASE_DIR, 'env', '.texmf-var')

    with tempfile.TemporaryDirectory() as tempdir:
        for i in range(2):
            process = Popen(
                ['xelatex', '-jobname', 'tmp', '-output-directory', tempdir, '-halt-on-error'],
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                env=env,
            )
            out, err = process.communicate(bytes(src, 'UTF-8'))
            if process.returncode or "No pages of output".encode() in out:
                # if not error:
                #    return self.render_to_pdf(
                #        r'\documentclass{minimal}\usepackage{xcolor}\begin{document}\textcolor{red}{ERROR IN TEXCODE}\begin{verbatim}'
                #        + '\n' + err.decode('UTF-8') + '\n' + out.decode('UTF-8') + '\n' + texcode
                #        + r'\end{verbatim}\end{document}', error=True
                #    )
                # else:

                pdf_obj.status = Pdf.FAILURE
                pdf_obj.save()
                return {'err': err.decode('UTF-8'), 'out': out.decode('UTF-8'),
                                                    'tex': src }

                # raise Exception()

        with open(os.path.join(tempdir, 'tmp.pdf'), 'rb') as f:
            pdf = f.read()

            pdf_obj.file = ContentFile(pdf, pdf_obj.name)
            pdf_obj.status = Pdf.SUCCESS
            pdf_obj.save()

@shared_task
def render_to_pdf(template_id, pdf_id, context=None):

    pdf_obj = Pdf.objects.get(id=pdf_id)

    if not context:
        context={}
    try:
        src = render_template(template_id, context)
    except Exception as e:
        pdf_obj.status = Pdf.ERROR
        pdf_obj.save()
        return {"err":repr(e),"context":context}
    try:
        import docker
        from docker.errors import ContainerError
        import socket
        import os
        from django.conf import settings
        import uuid
        from shutil import copyfile, rmtree

        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        this_container = client.containers.get(socket.gethostname())

        compose_proj = this_container.labels["com.docker.compose.project"]
        hostdir = [x["Source"] for x in this_container.attrs['Mounts'] if x["Destination"] == '/data/tex_share' and x["Type"] == "bind"][0]

        bdir = os.path.join(os.path.dirname(settings.BASE_DIR), 'tex_share')

        job = pdf_obj.task_id

        jobdir = os.path.join(bdir, "%s" % job)
        os.mkdir(jobdir)

        xi = client.images.get("%s_xelatex" % compose_proj)

        with open(os.path.join(jobdir, '%s.tex'%job), 'wb') as f:
            f.write(src.encode('UTF-8'))

        with open(os.path.join(jobdir,"make.sh"), 'w') as f:
            f.write("latexmk -xelatex -halt-on-error %s.tex\n"%job)
            f.write("echo $? > exit-code.int")

        os.mkdir(os.path.join(jobdir,"pdf"))

        for cpf in Template.objects.get(pk=template_id).files.all():
            #print(cpf.name)
            #print(cpf.name.split('/')[-1])
            #print(cpf.pure_name())
            destname = cpf.pure_name()
            if not destname.endswith(".pdf"):
                destname+=".pdf"
            with open(cpf.file.path,'rb') as fs, open(os.path.join(jobdir,"pdf",destname), 'wb') as fd:
                while True:
                    buf = fs.read(1024)
                    if buf:
                        n = fd.write(buf)
                    else:
                        break

        os.mkdir(os.path.join(jobdir, "flag"))

        for origin in Template.objects.get(pk=template_id).tournament.origin_set.all():
            if origin.flag_pdf:
                destname = origin.slug
                if not destname.endswith(".pdf"):
                    destname+=".pdf"
                with open(origin.flag_pdf.path,'rb') as fs, open(os.path.join(jobdir,"flag",destname), 'wb') as fd:
                    while True:
                        buf = fs.read(1024)
                        if buf:
                            n = fd.write(buf)
                        else:
                            break

        dfiles = {}
        for path, dirs, files in os.walk(jobdir):
            fs = []
            for f in files:
                fs.append(f)
            dfiles[path] = fs

        try:
            ct = client.containers.run(xi, '/bin/bash make.sh', working_dir="/data/src", detach=True, volumes={
                os.path.join(hostdir, "%s" % job): {'bind': '/data/src', 'mode': 'rw'}}, log_config={'type':'json-file'})
            ct.wait()
            err = ct.logs(stderr=True, stdout=False)
            out = ct.logs(stdout=True, stderr=False)
            #print("log output")
            #print(out)

        except ContainerError as e:

            pdf_obj.status = Pdf.ERROR
            pdf_obj.save()

            rmtree(jobdir)
            return {'err': repr(e), "context":context}

        try:
            ct.remove()
        except:
            pass

        try:
            with open(os.path.join(jobdir, 'exit-code.int'), 'rb') as f:
                exit_code = int(f.read().strip())
        except Exception as e:
            exit_code = 42

        if exit_code:
            pdf_obj.status = Pdf.FAILURE
            pdf_obj.save()
            rmtree(jobdir)
            return {'err': err.decode('UTF-8'), 'out': out.decode('UTF-8'), 'tex': src, "files":dfiles}

        with open(os.path.join(jobdir, '%s.pdf'%job), 'rb') as f:
            pdf = f.read()

            pdf_obj.file = ContentFile(pdf, pdf_obj.name)
            pdf_obj.status = Pdf.SUCCESS
            pdf_obj.save()

        rmtree(jobdir)
    except Exception as e:
        pdf_obj.status = Pdf.ERROR
        pdf_obj.save()

        return {'err': traceback.format_exc(), "context": context}
