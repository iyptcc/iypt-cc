FROM ubuntu:jammy

# Initialize
RUN mkdir -p /data/django
WORKDIR /data/django

# Setup
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y locales netcat python3 python3-pip python3-dev postgresql-client-14 libpq-dev git build-essential gettext libzbar0 poppler-utils libz-dev libjpeg-dev libfreetype6-dev libgl1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
RUN locale-gen en_US.UTF-8

RUN python3 -m pip install --upgrade pip

ARG CI_COMMIT_SHORT_SHA
RUN echo $CI_COMMIT_SHORT_SHA

RUN mkdir -p /data/django-git
RUN echo $CI_COMMIT_SHORT_SHA > /data/django-git/HEAD

# Prepare
COPY . /data/django/
RUN mkdir -p cc/static/admin

RUN python3 -m pip install --upgrade -r dep/requirements.pip

RUN /usr/bin/python3 manage.py collectstatic --noinput
