from PIL import Image

from apps.jury.models import JurorGrade


def fight_grades_valid(fight):
    vl = list(
        JurorGrade.objects.filter(stage_attendee__stage__fight=fight).values_list(
            "valid", flat=True
        )
    )
    return len(vl) > 0 and all(vl)


def check_fight_permission(user, fight):

    if user.has_perm("jury.change_all_jurorsessions"):
        return True
    if not user.has_perm("jury.change_jurorsession"):
        return False
    try:
        if (
            fight.operators.filter(id=user.profile.active_id).exists()
            and not fight.locked
        ):
            return True
    except:
        return False

    return False


areas = {
    "data": (-0.4, 1, 1, 0.7),
    "rep": (-1, 1, -0.3, 0.7),
    "opp": (-1, 0.3, -0.2, 0),
    "rev": (-1, -0.2, -0, -0.6),
    "full": (-1, 1, 1, -1),
}


def crop_image(img, box):
    w, h = img.size
    b = (
        int(((box[0] + 1) / 2) * w),
        int(h - ((box[1] + 1) / 2) * h),
        int(((box[2] + 1) / 2) * w),
        int(h - ((box[3] + 1) / 2) * h),
    )
    cr = img.crop(box=b)

    return cr


def orient_image(tosave, qr):
    left = qr.rect.left + (qr.rect.width / 2)
    top = qr.rect.top + (qr.rect.height / 2)
    print(tosave.width)

    if tosave.width < tosave.height:
        # portrait mode
        if left > (tosave.width / 2):
            # rotate left 90
            tosave = tosave.transpose(Image.ROTATE_90)
        else:
            # rotate right 90
            tosave = tosave.transpose(Image.ROTATE_270)

    else:
        if top > (tosave.height / 2):
            # rotate 180
            tosave = tosave.transpose(Image.ROTATE_180)

    return tosave
