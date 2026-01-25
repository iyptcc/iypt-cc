FROM ghcr.io/astral-sh/uv:debian

# Setup
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y locales netcat-openbsd postgresql-client libpq-dev build-essential gettext libzbar0 poppler-utils libz-dev libjpeg-dev libfreetype6-dev libgl1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


ENV LANG=en_US.UTF-8
RUN locale-gen en_US.UTF-8

# Initialize
RUN mkdir -p /data/django
WORKDIR /data/django

# RUN python3 -m pip install --upgrade pip

ARG CI_COMMIT_SHORT_SHA
RUN echo $CI_COMMIT_SHORT_SHA

RUN mkdir -p /data/django-git
RUN echo $CI_COMMIT_SHORT_SHA > /data/django-git/HEAD

# Prepare
COPY . /data/django/
RUN mkdir -p cc/static/admin

RUN uv venv
RUN uv pip install --upgrade -r dep/requirements.uv

RUN .venv/bin/python3 manage.py collectstatic --noinput
