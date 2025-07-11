from __future__ import absolute_import, unicode_literals

from datetime import datetime

import cv2
import paramiko
import pypdfium2 as pdfium
from celery import current_task, shared_task
from django.core.files.base import ContentFile
from django.core.signing import Signer

from apps.fight.models import ScanProcessing
from apps.jury.models import GradingSheet, JurorSession
from apps.plan.models import Stage
from apps.printer.models import FileServer, ORMHostKeyPolicy, Pdf

from .utils import crop_image, draw_bbox, orient_image, sheet_areas


@shared_task
def processJob(tournament_id, pdf_id):
    pages = {}

    pdf = Pdf.objects.get(pk=pdf_id)
    doc = pdfium.PdfDocument(pdf.file.path)
    qcd = cv2.wechat_qrcode_WeChatQRCode()
    signer = Signer()

    ar = ScanProcessing.objects.get(task_id=current_task.request.id)

    for pagenr, page in enumerate(doc):
        page_meta = {}
        # scale=4: 4*72 dpi = 288 dpi instead of the previous 300
        image = page.render(
            scale=4,
            rotation=0,
        ).to_numpy()
        tosave = image
        data, position = qcd.detectAndDecode(image)

        # this should never happen with WeChat QR detector as it
        # has an internal upscaling mechanism
        if len(data) == 0:
            page_meta["hires"] = True
            tosave = page.render(
                scale=9,
                rotation=0,
            ).to_numpy()
            data, position = qcd.detectAndDecode(image)

        if len(data) and len(position):
            # draw_bbox(tosave, position)
            tosave = orient_image(tosave, position[0])

            dat = data[0]
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
                    r, jpg_buf = cv2.imencode(
                        ".jpg", crop_image(tosave, sheet_areas[area])
                    )
                    cf[area] = ContentFile(
                        jpg_buf.data, "%s-%d-%d.jpg" % (area, js.id, stage.id)
                    )

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
            # cv2.imwrite("parts/error-%d.jpg" % (pagenr + 1), tosave)

        pages[pagenr + 1] = page_meta
        # tosave = cv2.rotate(tosave, cv2.ROTATE_90_CLOCKWISE)
        # cv2.imshow("Image", tosave)

        # cv2.imwrite("parts/rev-%d.jpg" % (pagenr + 1), )

        # cv2.imwrite("parts/full-%d.jpg" % (pagenr + 1), tosave)

        current_task.update_state(
            state="PROGRESS", meta={"current": pagenr, "total": len(doc)}
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
