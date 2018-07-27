
from datetime import datetime

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session


def purge_sessions(tournament):

    sessions = Session.objects.exclude(expire_date__lte=datetime.now())
    logged_in = [s.session_key for s in sessions if s.get_decoded().get("results-auth-%s"%tournament.slug)]

    for session_key in logged_in:
        s = SessionStore(session_key=session_key)
        s["results-auth-%s"%tournament.slug] = False
        s.save()
        s.modified
