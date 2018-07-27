import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc.settings")

print(os.path.abspath(__file__ + "/../../"))

sys.path.append(os.path.abspath(__file__ + "/../../"))

import django
django.setup()

from django.contrib.auth.models import User

from apps.account.models import ActiveUser

root = None
try:
    root = User.objects.get(username="root")
except:
    root=User.objects.create(username="root",email="fe-x@nlogn.org",is_staff=True,is_superuser=True,password="pbkdf2_sha256$30000$bfSRcz8435Km$VOJasXkSscLPajzWpi3An2aA8YKkn9keyX/FGassy/k=")

au = ActiveUser.objects.get_or_create(user=root)
