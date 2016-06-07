#!/bin/sh -e

if [ `uname` != "Darwin" ]; then
    run_opts="`id -u`:`id -g`"
fi

err=0
for f in docker/Dockerfile.*.build; do
    imagename=`python -c 'import sys,uuid; sys.stdout.write(str(uuid.uuid4()))'`
    docker build -t ${imagename} -f ${f} .
    docker run --rm -v ${PWD}:${PWD} -v /var/run/docker.sock:/var/run/docker.sock ${run_opts} -w ${PWD} ${imagename} py.test --cov caduc --cov-report term-missing tests/ || err=1
done

exit ${err}
