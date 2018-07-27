FROM ubuntu:rolling

# Initialize
RUN mkdir -p /data/django
WORKDIR /data/django

# Setup
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y locales netcat python3 python3-pip python3-dev postgresql-client-10 libpq-dev git build-essential gettext && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
RUN locale-gen en_US.UTF-8

RUN pip3 install --upgrade pip

# Prepare
COPY . /data/django/
RUN mkdir -p cc/static/admin

RUN pip3 install --upgrade -r dep/requirements.pip

RUN mkdir -p /data/src/
RUN cd /data/src/ && git clone https://github.com/felix-engelmann/django-formtools && \
    cd django-formtools && git checkout 65c9a1c0669784c32e5466b1c5bb10cf90e438d8
RUN cd /data/src/django-formtools  && \
    /usr/bin/python3 setup.py install

RUN /usr/bin/python3 manage.py collectstatic --noinput
