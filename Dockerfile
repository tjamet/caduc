FROM python:2.7-alpine

RUN apk update && apk add git

ADD . /tmp/srcs
RUN cd /tmp/srcs && python setup.py install

ENTRYPOINT ["/usr/local/bin/caduc"]
