FROM python:2.7

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y git python-setuptools && apt-get clean

ADD . /tmp/srcs
RUN cd /tmp/srcs && python setup.py install

ENTRYPOINT ["/usr/local/bin/caduc"]
