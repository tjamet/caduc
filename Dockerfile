FROM python:2.7-alpine


RUN apk update && apk add git

ADD . /tmp/srcs
RUN cd /tmp/srcs && python setup.py install

ENTRYPOINT ["/usr/local/bin/caduc"]
LABEL io.whalebrew.name=caduc io.whalebrew.config.environment='["DOCKER_HOST"]' io.whalebrew.config.volumes='["/var/run/docker.sock:/var/run/docker.sock"]'
