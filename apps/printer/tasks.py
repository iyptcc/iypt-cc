from __future__ import absolute_import, unicode_literals

import time
import traceback

from celery import current_task, shared_task, states
from django.conf import settings
from django.core.files.base import ContentFile

from apps.printer.models import Pdf, Template

from .utils import render_template


def get_source(template_id, pdf_obj, context):
    if not context:
        context = {}
    try:
        (src, err) = render_template(template_id, context)
    except Exception as e:
        pdf_obj.status = Pdf.ERROR
        pdf_obj.save()
        return {"err": repr(e), "context": context}
    if err is not None:
        pdf_obj.status = Pdf.ERROR
        pdf_obj.save()
        return {"err": err, "context": context}
    return src


@shared_task
def render_to_pdf_local(template_id, pdf_id, context=None):

    pdf_obj = Pdf.objects.get(id=pdf_id)

    src = get_source(template_id, pdf_obj, context)
    if type(src) != str:
        return src

    import os
    import tempfile
    from subprocess import PIPE, Popen

    env = os.environ.copy()
    env["TEXMFHOME"] = os.path.join(settings.BASE_DIR, "tex", "texmf")
    # env["OPENTYPEFONTS"] = ':' + os.path.join(settings.BASE_DIR, 'cc', 'static', 'ssp', 'OTF') + ':'
    # env["TTFONTS"] = ':' + os.path.join(settings.BASE_DIR, 'cc', 'static', 'ssp', 'TTF') + ':'
    # env["TEXMFVAR"] = os.path.join(settings.BASE_DIR, 'env', '.texmf-var')

    with tempfile.TemporaryDirectory() as tempdir:
        for i in range(2):
            process = Popen(
                [
                    "xelatex",
                    "-jobname",
                    "tmp",
                    "-output-directory",
                    tempdir,
                    "-halt-on-error",
                ],
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                env=env,
            )
            out, err = process.communicate(bytes(src, "UTF-8"))
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
                return {
                    "err": err.decode("UTF-8"),
                    "out": out.decode("UTF-8"),
                    "tex": src,
                }

                # raise Exception()

        with open(os.path.join(tempdir, "tmp.pdf"), "rb") as f:
            pdf = f.read()

            pdf_obj.file = ContentFile(pdf, pdf_obj.name)
            pdf_obj.status = Pdf.SUCCESS
            pdf_obj.save()


@shared_task
def render_to_pdf(template_id, pdf_id, context=None):

    try:
        if settings.LATEX_RENDER_DIRECT:
            return render_to_pdf_local(template_id, pdf_id, context=context)
    except:
        pass

    pdf_obj = Pdf.objects.get(id=pdf_id)

    src = get_source(template_id, pdf_obj, context)
    if type(src) != str:
        return src

    try:
        import os
        import socket
        import uuid
        from shutil import copyfile, rmtree

        import docker
        from docker.errors import ContainerError

        client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        hostname = socket.gethostname()

        try:
            all_ct_list = client.containers.list()
        except Exception as e:
            time.sleep(5)
            print("first client containers failed", e.__repr__())
            all_ct_list = client.containers.list()

        this_container = list(
            filter(lambda c: c.attrs["Config"]["Hostname"] == hostname, all_ct_list)
        )[0]

        compose_proj = this_container.labels["com.docker.compose.project"]
        hostdir = [
            x["Source"]
            for x in this_container.attrs["Mounts"]
            if x["Destination"] == "/data/tex_share" and x["Type"] == "bind"
        ][0]

        bdir = os.path.join(os.path.dirname(settings.BASE_DIR), "tex_share")

        job = pdf_obj.task_id

        jobdir = os.path.join(bdir, "%s" % job)
        os.mkdir(jobdir)

        if settings.XELATEX_IMAGE_NAME:
            xi = client.images.get(settings.XELATEX_IMAGE_NAME)
        else:
            xi = client.images.get("%s_xelatex" % compose_proj)

        with open(os.path.join(jobdir, "%s.tex" % job), "wb") as f:
            f.write(src.encode("UTF-8"))

        with open(os.path.join(jobdir, "make.sh"), "w") as f:
            f.write("latexmk -xelatex -halt-on-error %s.tex\n" % job)
            f.write("echo $? > exit-code.int")

        os.mkdir(os.path.join(jobdir, "pdf"))

        for cpf in Template.objects.get(pk=template_id).files.all():
            # print(cpf.name)
            # print(cpf.name.split('/')[-1])
            # print(cpf.pure_name())
            destname = cpf.pure_name()
            if not destname.endswith(".pdf"):
                destname += ".pdf"
            with open(cpf.file.path, "rb") as fs, open(
                os.path.join(jobdir, "pdf", destname), "wb"
            ) as fd:
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
                    destname += ".pdf"
                with open(origin.flag_pdf.path, "rb") as fs, open(
                    os.path.join(jobdir, "flag", destname), "wb"
                ) as fd:
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
            ct = client.containers.run(
                xi,
                "/bin/bash make.sh",
                working_dir="/data/src",
                detach=True,
                volumes={
                    os.path.join(hostdir, "%s" % job): {
                        "bind": "/data/src",
                        "mode": "rw",
                    }
                },
                log_config={"type": "json-file"},
                network_mode="none",
            )
            ct.wait()
            err = ct.logs(stderr=True, stdout=False)
            out = ct.logs(stdout=True, stderr=False)
            # print("log output")
            # print(out)

        except ContainerError as e:

            pdf_obj.status = Pdf.ERROR
            pdf_obj.save()

            rmtree(jobdir)
            return {"err": repr(e), "context": context}

        try:
            ct.remove()
        except:
            pass

        try:
            with open(os.path.join(jobdir, "exit-code.int"), "rb") as f:
                exit_code = int(f.read().strip())
        except Exception as e:
            exit_code = 42

        if exit_code:
            pdf_obj.status = Pdf.FAILURE
            pdf_obj.save()
            rmtree(jobdir)
            return {
                "err": err.decode("UTF-8"),
                "out": out.decode("UTF-8"),
                "tex": src,
                "files": dfiles,
            }

        with open(os.path.join(jobdir, "%s.pdf" % job), "rb") as f:
            pdf = f.read()

            pdf_obj.file = ContentFile(pdf, pdf_obj.name)
            pdf_obj.status = Pdf.SUCCESS
            pdf_obj.save()

        rmtree(jobdir)
    except Exception as e:
        pdf_obj.status = Pdf.ERROR
        pdf_obj.save()

        return {"err": traceback.format_exc(), "context": context}
