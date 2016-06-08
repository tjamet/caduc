import caduc.timer
import docker
import docker.utils
import sys
import time
import threading
import unittest

from caduc.cmd import create_watcher
from .. import mock

e = None
no_docker = False
try:
    docker.Client(**docker.utils.kwargs_from_env(assert_hostname=False)).version()
except Exception as e:
    no_docker = True


class WatchThread(threading.Thread):

    def __init__(self, watcher):
        self.watcher = watcher
        super(WatchThread, self).__init__()

    def run(self):
        self.watcher.watch()


@unittest.skipIf(no_docker, "Failed to connect to docker host, error: %s" % e)
class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.client = docker.Client(**docker.utils.kwargs_from_env(assert_hostname=False))
        options = mock.Mock()
        options.debug = False
        options.config = ['images.test-*.grace_time=1s']
        options.config_path = None
        options.image_gracetime = '1d'
        self.options = options
        self.containers = set()
        self.images = set()

    def tearDown(self):
        caduc.timer.Timer.CancelAll()
        self.watchThread._Thread__stop()
        for container in self.containers :
            try:
                self.client.remove_container(container)
            except:
                pass
        for image in self.images:
            try:
                self.client.remove_image(image)
            except:
                pass

    def start_watch(self):
        self.watcher = create_watcher(self.options, [])
        self.watchThread = WatchThread(self.watcher)
        self.watchThread.start()

    def wait_for(self, f, expectation):
        value = f()
        for i in range(20):
            if f()==expectation:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("Failed to match %s with expectation: (== %s)" % (value, expectation))

    def wait_for_not(self, f, expectation):
        value = f()
        for i in range(20):
            if f()!=expectation:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("Failed to match %s with expectation: (!= %s)" % (value, expectation))

    def test_image_requirement_is_monitored_and_deleted(self):
        self.start_watch()
        for line in self.client.build("tests/fixtures/images", 'test-image-build'):
            sys.stdout.write(line)
        def get(dct, key):
            try:
                return dct[key]
            except KeyError:
                return None
        self.wait_for_not(lambda: get(self.watcher.images, 'test-image-build'), None)
        self.wait_for_not(lambda: self.watcher.images['test-image-build'].event, None)

        container = self.client.create_container('test-image-build', command='tail -f /dev/null', tty=True)
        self.containers.add(container['Id'])
        self.wait_for_not(lambda: get(self.watcher.containers, container['Id']), None)
        self.wait_for(lambda: self.watcher.images['test-image-build'].event, None)

        self.client.remove_container(container['Id'])
        self.containers.remove(container['Id'])
        container_removal = time.time()

        self.wait_for(lambda: get(self.watcher.containers, container['Id']), None)
        self.wait_for_not(lambda: get(self.watcher.images, 'test-image-build'), None)

        self.wait_for_not(lambda: self.watcher.images['test-image-build'].event, None)

        self.wait_for(lambda: get(self.watcher.images, 'test-image-build'), None)
        self.assertAlmostEqual(time.time() - container_removal, 1, places=0) 

