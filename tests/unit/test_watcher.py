import caduc.watcher
import docker.errors
import sure
import unittest

from .. import mock

class TestWatcher(unittest.TestCase):
    def setUp(self):
        self.client = mock.Mock()
        self.images = {}
        self.containers = mock.Mock()
        self.watcher = caduc.watcher.Watcher(lambda: self.client, self.images, self.containers)
        self.dockerErrorsNotFound = docker.errors.NotFound

    def tearDown(self):
        docker.errors.NotFound = self.dockerErrorsNotFound

    def mock_image(self, name='event.id', attribute='refresh'):
        image = mock.Mock()
        setattr(image, attribute, mock.Mock())
        self.images[name] = image
        return image

    def create_event(self, **kwds):
        if 'id' not in kwds:
            kwds['id'] = 'event.id'
        return kwds

    def test_tag(self):
        image = self.mock_image(attribute='refresh')
        self.watcher.tag(self.create_event())
        image.refresh.assert_called_once_with()

    def test_untag(self):
        image = self.mock_image(attribute='refresh')
        self.watcher.untag(self.create_event())
        image.refresh.assert_called_once_with()
        # Check that untag succeeds with unkwnown image
        self.watcher.untag(self.create_event(id='non-existing-event'))

        docker.errors.NotFound = Exception
        image.refresh.side_effect = Exception
        self.watcher.untag(self.create_event())

    def test_delete(self):
        image = self.mock_image(name='image.id')
        self.watcher.delete(self.create_event(id='image.id'))
        self.images.should_not.contain('image.id')

        self.watcher.delete(self.create_event())

    def test_create(self):
        self.containers.add = mock.Mock()
        self.watcher.create(self.create_event(id='container.id', Type='container'))
        self.containers.add.assert_called_once_with('container.id')

    def test_destroy(self):
        self.containers.pop = mock.Mock()
        self.watcher.destroy(self.create_event(id='container.id', Type='container'))
        self.containers.pop.assert_called_once_with('container.id')

        self.containers.pop.side_effect = KeyError
        self.watcher.destroy(self.create_event(id='container.id', Type='container'))

    def test_watch(self):
        self.watcher.destroy = mock.Mock()
        self.watcher.create = mock.Mock()
        self.watcher.delete = mock.Mock()
        self.watcher.untag = mock.Mock(side_effect=Exception)
        self.client.events = mock.Mock(return_value = [
            self.create_event(id='id1', Action='commit'),
            self.create_event(id='id2', Action='unknown'),
            self.create_event(id='id3', Action='destroy'),
            self.create_event(id='id4', Action='create'),
            self.create_event(id='id5', Action='untag'),
            self.create_event(id='id6', Action='delete'),
        ])
        self.watcher.watch()
        self.watcher.destroy.assert_called_once_with(dict(id='id3', Action='destroy'))
        self.watcher.create.assert_called_once_with(dict(id='id4', Action='create'))
        self.watcher.untag.assert_called_once_with(dict(id='id5', Action='untag'))
        self.watcher.delete.assert_called_once_with(dict(id='id6', Action='delete'))

    def test_watch_calls_handle(self):
        self.watcher.handle = mock.Mock()
        self.client.events = mock.Mock(return_value = [
            self.create_event(id='id1', Action='commit'),
            self.create_event(id='id2', Action='unknown'),
        ])
        self.watcher.watch()
        self.assertEquals(
            self.watcher.handle.mock_calls,
            [
                mock.call({'id': 'id1', 'Action': 'commit'}),
                mock.call({'id': 'id2', 'Action': 'unknown'}),
            ]
        )
