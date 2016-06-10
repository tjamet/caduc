import caduc.timer
import caduc.image
import docker
import docker.utils
import docker.errors
import logging
import pytest
import sys
import time
import sure
import unittest

from caduc.cmd import create_watcher
from .. import mock

docker_error = None
no_docker = False
try:
    docker.Client(**docker.utils.kwargs_from_env(assert_hostname=False)).version()
except Exception as e:
    docker_error = e
    no_docker = True


class ControlledTimer(object):
    def __init__(self, delay, cb):
        self.cb = cb
        self.delay = delay
        self.started = False

    def start(self):
        self.started = True

    def cancel(self):
        self.started = False

    def _trigger(self):
        if not self.started:
            raise RuntimeError("Cannot trigger a non started timer on %r" % self.cb)
        self.cb()

    def __str__(self):
        return "<Timer: delay: %s started: %s>" % (self.delay, self.started)

@unittest.skipIf(no_docker, "Failed to connect to docker host, error: %s" % docker_error)
class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger(type(self).__name__)
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
        for container in self.containers :
            try:
                self.client.remove_container(container,
                    v=True,
                    force=True
                )
            except:
                pass
        for image in self.images:
            try:
                self.client.remove_image(image,
                    force=True
                )
            except:
                pass

    def build_test_image(self, image_name):
        for line in self.client.build("tests/fixtures/images", image_name):
            sys.stdout.write(line)
        self.images.add(image_name)

    def start_test_container(self, image_name):
        container = self.client.create_container('test-image-build', command='tail -f /dev/null', tty=True)
        self.containers.add(container['Id'])
        return container
 
    def remove_test_container(self, container):
        self.client.remove_container(container,
            v=True,
            force=True
        )
        try:
            if isinstance(container, dict):
                self.containers.remove(container['Id'])
            else:
                self.containers.remove(container)
        except:
            pass

    def dict_intersect(self, d1, d2):
        """
        Returns the shared definition of 2 dicts
        """
        common_keys = set(d1.keys()) & set(d2.keys())
        r = {}
        for key in common_keys:
            if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                r[key] = self.dict_intersect(d1[key], d2[key])
            else:
                if d1[key] == d2[key]:
                    r[key] = d1[key]
        return r

    def wait_for_event(self, listener, watcher, event):
        for e in listener:
            watcher.handle(e)
            common = self.dict_intersect(e,event)
            self.logger.info('event: %r, waiting for: %r, shared keys: %r', e, event, common)
            if common == event:
                return

    @mock.patch('caduc.image.Image.Timer', new=ControlledTimer)
    @pytest.mark.timeout(5)
    def test_image_tag_plans_image_deletion(self):
        watcher = create_watcher(self.options, [])
        listener = self.client.events(decode=True)
        self.build_test_image('test-image-build')
        self.wait_for_event(listener, watcher, {
                'Action':'tag',
                'Actor': {
                    'Attributes':{
                        'name':'test-image-build:latest'
                     }
                 }
            }
        )
        watcher.images['test-image-build'].event.should.not_be(None)
        watcher.images['test-image-build'].event.started.should.be.truthy
        watcher.images['test-image-build'].event.delay.should.be.eql(1)

    @mock.patch('caduc.image.Image.Timer', new=ControlledTimer)
    @pytest.mark.timeout(5)
    def test_existing_image_deletion_is_planned(self):
        self.build_test_image('test-image-build')
        watcher = create_watcher(self.options, [])
        self.logger.info(watcher.images['test-image-build'])
        watcher.images['test-image-build'].event.should.not_be(None)
        watcher.images['test-image-build'].event.started.should.be.truthy

    @mock.patch('caduc.image.Image.Timer', new=ControlledTimer)
    @pytest.mark.timeout(5)
    def test_container_creation_cancels_image_deletion(self):
        self.build_test_image('test-image-build')
        watcher = create_watcher(self.options, [])
        old_event = watcher.images['test-image-build'].event

        listener = self.client.events(decode=True)
        container = self.start_test_container('test-image-build')

        self.wait_for_event(listener, watcher, {
            'Action': 'create',
            'Type': 'container',
        })

        old_event.started.should.not_be.truthy
        watcher.images['test-image-build'].event.should.be(None)

    @mock.patch('caduc.image.Image.Timer', new=ControlledTimer)
    @pytest.mark.timeout(5)
    def test_container_removal_schedules_image_removal(self):
        self.build_test_image('test-image-build')

        container = self.start_test_container('test-image-build')

        listener = self.client.events(decode=True)
        watcher = create_watcher(self.options, [])
        self.remove_test_container(container)

        self.wait_for_event(listener, watcher, {
            'Action': 'destroy',
        })

        watcher.images['test-image-build'].event.should.not_be(None)
        watcher.images['test-image-build'].event.started.should.be.truthy
        watcher.images['test-image-build'].event.delay.should.eql(1)

    @mock.patch('caduc.image.Image.Timer', new=ControlledTimer)
    @pytest.mark.timeout(5)
    def test_container_removal_schedules_image_removal(self):
        self.build_test_image('test-image-build')

        listener = self.client.events(decode=True)
        watcher = create_watcher(self.options, [])

        watcher.images['test-image-build'].event._trigger()

        self.wait_for_event(listener, watcher, {
            'Action': 'delete',
        })
