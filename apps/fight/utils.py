from enum import IntEnum

import cv2

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


sheet_areas = {
    "data": (-0.4, 1, 1, 0.7),
    "rep": (-1, 1, -0.3, 0.7),
    "opp": (-1, 0.3, -0.2, 0),
    "rev": (-1, -0.2, -0, -0.6),
    "full": (-1, 1, 1, -1),
}


class PilRotation(IntEnum):
    """Rotation enums that are compatible with PIL.Image.Transpose"""

    ROTATE_90 = 2
    ROTATE_180 = 3
    ROTATE_270 = 4


def crop_image(img, box):
    """Return part of an image given bounding box in coordinates from range [-1,1]"""
    # image is in matrix coordinates, origin is top left and (row (y), column (x))
    h, w, *ch = img.shape
    b = (
        int(((box[0] + 1) / 2) * w),
        int(h - ((box[1] + 1) / 2) * h),
        int(((box[2] + 1) / 2) * w),
        int(h - ((box[3] + 1) / 2) * h),
    )
    cr = img[b[1] : b[3], b[0] : b[2]]

    return cr


def orient_image(tosave, rect):
    # points are in image coordinates, origin top left and (x (column), y (row))
    # assume that WeChat QR detector always gives the top left corner first,
    # then the other corners in clockwise direction
    tl = tuple(rect[0])
    tr = tuple(rect[1])
    br = tuple(rect[2])
    bl = tuple(rect[3])

    # image size is in matrix coordinates, origin top left and (row (y), column (x))
    # print(tosave.shape)
    img_width = tosave.shape[1]
    img_height = tosave.shape[0]

    # left and top were the center coordinates of the QR code in a previous version
    # now they are the top left corner coordinates, hopefully this does not make a difference
    left = tl[0]
    top = tl[1]
    if img_width < img_height:
        # portrait mode
        if left > (img_width / 2):
            # rotate left 90
            tosave = cv2.rotate(tosave, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            # rotate right 90
            tosave = cv2.rotate(tosave, cv2.ROTATE_90_CLOCKWISE)
    else:
        if top > (img_height / 2):
            # rotate 180
            tosave = cv2.rotate(tosave, cv2.ROTATE_180)

    return tosave


def draw_bbox(image, bbox):
    """Draw a box using the bounding box coordinates from WeChat QR Code detector"""
    # Colors are red, green, blue, yellow. If you see cyan, your channels are messed up
    colors = ((0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255))
    if bbox:
        bbox = [bbox[0].astype(int)]
        n = len(bbox[0])
        for i in range(n):
            cv2.line(
                image,
                tuple(bbox[0][i]),
                tuple(bbox[0][(i + 1) % n]),
                colors[i % len(colors)],
                3,
            )
