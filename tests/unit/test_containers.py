import caduc.containers
import caduc.dicts
import faker
import sure
import unittest

from .. import mock

class TestContainers(unittest.TestCase):

    def setUp(self):
        self.faker = faker.Faker()

    def getClient(self):
        return self.client

    def getContainers(self):
        self.client = mock.Mock()
        self.config = mock.Mock()
        self.client.containers = mock.Mock(return_value = [])
        self.images = {}
        return caduc.containers.Containers(self.config, self.getClient, self.images)

    def test_instanciate(self):
        containers = self.getContainers()
        self.client.inspect_container = mock.Mock(return_value=dict(Id='container.id', Image='image.id'))
        image = mock.Mock()
        image.add = mock.Mock()

        containers.instanciate('container.id')
        image.add.assert_not_called()

        self.images['image.id'] = image

        containers.instanciate('container.id')
        self.images['image.id'].add.assert_called_once_with(mock.ANY)

    def test_list_items(self):
        containers = self.getContainers()
        self.client.containers.reset_mock()
        containers.list_items()
        self.client.containers.assert_called_once_with(all=True)

    def test_inspect(self):
        containers = self.getContainers()
        self.client.inspect_container = mock.Mock(return_value=dict(Id='some.value'))
        for args, kwds in [
                (tuple(), {}),
                (('abc',), {}),
                (tuple(), {'key': 'value'}),
                (('value',), {'key': 'value2'}),
            ]:
            self.client.inspect_container.reset_mock()
            containers.inspect.when.called_with(*args, **kwds).should.return_value(dict(Id='some.value'))
            self.client.inspect_container.assert_called_once_with(*args, **kwds)

    def test_pop_notifies_image(self):
        containers = self.getContainers()
        pop = caduc.dicts.SyncDict.pop
        image = mock.Mock()
        image.remove = mock.Mock()
        self.images['image.id'] = image
        try:
            caduc.dicts.SyncDict.pop = mock.Mock(return_value = None)
            containers.pop.when.called_with('some.key').should.return_value(None)

            client = mock.Mock()
            client.inspect_container = mock.Mock(return_value=dict(
                Id = 'image.id',
                Name = 'Name',
                Image = 'Image',
            ))

            container = caduc.container.Container(None, lambda: client, 'image.id')
            container.image_id = 'image.id'
            caduc.dicts.SyncDict.pop = mock.Mock(return_value = container)
            containers.pop.when.called_with('some.key').should.return_value(container)
            image.remove.assert_called_once_with(container)

            # when containers are running on unknown images
            # we should go-on running
            client = mock.Mock()
            client.inspect_container = mock.Mock(return_value=dict(
                Id = 'image.id',
                Name = 'Name',
                Image = 'Image',
            ))

            container = caduc.container.Container(None, lambda: client, 'image.id')
            caduc.dicts.SyncDict.pop = mock.Mock(return_value = container)
            containers.pop.when.called_with('some.key').should.return_value(container)
        finally:
            caduc.dicts.SyncDict.pop = pop

