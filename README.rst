Continuous Delayed Docker Cleanup
=================================
CDDC watched changes on the docker engine to schedule unused image removal.
A gracetime is observed between the removal of a container and removal of the image

How To
======

Install
-------

Install the tool by launching ``python setup.py install`` as root or ``python setup.py install --user``
If you do not have root acces or do not want to bother your co-workers on the same host

Use
---

Setup your environment so that ``docker ps`` returns the list of running containers
To delete images one hour after removal of the last container running them, simply run ``cddc --image-gracetime="1h"``.

The default gracetime is of 1 day.

