from __future__ import absolute_import, unicode_literals

from datetime import datetime
from io import BytesIO

import paramiko
from celery import current_task, shared_task
from django.core.files.base import ContentFile
from django.core.signing import Signer
from pdf2image import convert_from_bytes, convert_from_path
from pyzbar.pyzbar import ZBarSymbol, decode

from apps.fight.models import ScanProcessing
from apps.jury.models import GradingSheet, JurorSession
from apps.plan.models import Stage
from apps.printer.models import FileServer, Pdf

from ..printer.views import ORMHostKeyPolicy
from .utils import areas, crop_image, orient_image


@shared_task
def processJob(tournament_id, pdf_id):
    pages = {}

    pdf = Pdf.objects.get(pk=pdf_id)
    images = convert_from_path(pdf.file.path, dpi=300, fmt="jpg")
    signer = Signer()

    ar = ScanProcessing.objects.get(task_id=current_task.request.id)

    for page, image in enumerate(images):
        page_meta = {}
        tosave = image
        data = decode(image, symbols=[ZBarSymbol.QRCODE])

        if len(data) == 0:
            page_meta["hires"] = True
            tosave = convert_from_path(
                pdf.file.path,
                first_page=page + 1,
                last_page=page + 1,
                dpi=600,
                fmt="jpg",
            )[0]
            data = decode(
                tosave, symbols=[ZBarSymbol.QRCODE]
            )  # if len(data) == 0:  #    print("decode 600")  #    tosave = convert_from_path(pdfname, first_page=page + 1, last_page=page + 1, dpi=600, fmt='jpg')[0]  #    data = decode(tosave)

        if len(data):
            tosave = orient_image(tosave, data[0])

            dat = data[0].data.decode()
            parts = dat.split(":")
            sig = signer.sign(parts[0])
            if len(parts[1]) >= 1 and sig[: len(dat)] == dat:
                page_meta["signature_valid"] = True
            else:
                page_meta["signature_valid"] = False
            if parts[0][:2] != "js":
                page_meta["jurorsession"] = False
                continue

            jsid = parts[0].split("_")
            page_meta["id"] = parts[0][2:]
            try:
                js = JurorSession.objects.get(
                    juror__attendee__tournament_id=tournament_id, pk=int(jsid[0][2:])
                )
                # print("file for js:",js)
                stage = js.fight.stage_set.get(order=jsid[1])
                # print("and stage:", stage)

                cf = {}
                for area in ["data", "rep", "opp", "rev", "full"]:
                    f = BytesIO()
                    try:
                        crop_image(tosave, areas[area]).save(f, format="jpeg")
                        cf[area] = ContentFile(
                            f.getvalue(), "%s-%d-%d.jpg" % (area, js.id, stage.id)
                        )
                    finally:
                        f.close()

                gsl = GradingSheet.objects.filter(jurorsession=js, stage=stage)
                if not gsl.exists():
                    gs = GradingSheet.objects.create(
                        jurorsession=js,
                        stage=stage,
                        process_job=ar,
                        header=cf["data"],
                        rep=cf["rep"],
                        opp=cf["opp"],
                        rev=cf["rev"],
                        full=cf["full"],
                    )
                    page_meta.update({"sheet_id": gs.id})
                else:
                    page_meta.update(
                        {
                            "error": "exists",
                            "sheet_id": gsl.first().id,
                            "text": "Grade sheet already in the system",
                        }
                    )

            except Exception as e:
                page_meta.update({"error": "failure", "text": "%s" % str(e)})

        else:
            page_meta.update({"error": "QR", "text": "no QR detected"})

        pages[page + 1] = page_meta
        # tosave = tosave.transpose(Image.ROTATE_270)

        # tosave.show()

        # .save("parts/rev-%d.jpg" % (page + 1))
        # tcrop(tosave, areas["opp"]).show()
        # tcrop(tosave, areas["rev"]).show()

        # dat.show()

        # tosave.save("parts/full-%d.jpg" % (page + 1))

        # dat.save("parts/data-%d.jpg" % (page + 1))  # .save('seite-%d.jpg'%(page+1))

        current_task.update_state(
            state="PROGRESS", meta={"current": page, "total": len(images)}
        )

    ar.finished = datetime.now()
    ar.save()

    return pages


@shared_task
def importSlides(server_id, path, jobs):
    print("background import at ", path)
    try:
        server = FileServer.objects.get(id=server_id)
        print("use server", server)
        ssh = paramiko.SSHClient()
        print("opened client", ssh)
        policy = ORMHostKeyPolicy(server)
        ssh.set_missing_host_key_policy(policy)
        print("set policy")
        ssh.connect(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            password=server.password,
        )
        sftp = ssh.open_sftp()
    except Exception as e:
        print("error opening conection", e.__repr__())
    print("connection opened")
    sftp.chdir(path)

    print("switch to path")
    print("jobs", jobs)
    for job in jobs:
        print("proc", job)
        stage = Stage.objects.get(id=job["stage_id"])
        rf = sftp.open(job["sub_path"])
        data = rf.read()
        cf = ContentFile(data, job["sub_path"])
        stage.pdf_presentation = cf
        stage.save()
        print("imported")
