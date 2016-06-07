FROM python:3.5-alpine

RUN apk update && apk add git

RUN pip install pyinstaller==3.1.1

ADD requirements.txt /tmp/requirements.txt
ADD requirements-dev.txt /tmp/requirements-dev.txt

RUN pip install -r /tmp/requirements.txt -r /tmp/requirements-dev.txt

