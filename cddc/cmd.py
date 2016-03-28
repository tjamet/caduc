#/usr/bin/env python

import docker
import logging
import os
import sys

if __name__=='__main__':
    sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '..'))

from cddc.containers import Containers
from cddc.images import Images
from cddc.watcher import Watcher

logging.basicConfig(level=logging.INFO)

DEFAULT_DELETE_TIMEOUT = "1d"

def main(argv=sys.argv[1:]):

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--image-gracetime", dest="image_gracetime", default=DEFAULT_DELETE_TIMEOUT,
                      help="Default grace TIME between last container removal (or last child image removal) and proper image removal", metavar="TIME")
    (options, args) = parser.parse_args(argv)

    client = docker.Client(**docker.utils.kwargs_from_env(assert_hostname=False))
    images = Images(client, default_timeout=options.image_gracetime)
    containers = Containers(client, images)
    images.update_timers()
    Watcher(client, images, containers).watch()

if __name__=='__main__':
    main()

