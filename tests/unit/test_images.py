import caduc.images
import caduc.dicts
import faker
import six
import sure
import unittest

from .. import mock

class TestImages(unittest.TestCase):

    def setUp(self):
        self.faker = faker.Faker()

    def getClient(self):
        return self.client

    def getImages(self):
        self.client = mock.Mock()
        self.config = mock.Mock()
        self.client.images = mock.Mock(return_value = [])
        self.timeout = 20
        return caduc.images.Images(self.config, self.getClient, self.timeout)

    def test_instanciate(self):
        images = self.getImages()
        image = mock.Mock()
        caduc.images.Image = mock.Mock(return_value=image)
        images.instanciate('some.item')
        caduc.images.Image.assert_called_once_with(self.config, images, self.getClient, 'some.item', self.timeout)

    def test_list_items(self):
        images = self.getImages()
        self.client.images.reset_mock()
        images.list_items()
        self.client.images.assert_called_once_with(all=True)

    def test_inspect(self):
        images = self.getImages()
        self.client.inspect_image = mock.Mock(return_value=dict(Id='some.value'))
        for args, kwds in [
                (tuple(), {}),
                (('abc',), {}),
                (tuple(), {'key': 'value'}),
                (('value',), {'key': 'value2'}),
            ]:
            self.client.inspect_image.reset_mock()
            images.inspect.when.called_with(*args, **kwds).should.return_value(dict(Id='some.value'))
            self.client.inspect_image.assert_called_once_with(*args, **kwds)

    def test_pop_notifies_image_deletion(self):
        images = self.getImages()
        pop = caduc.dicts.SyncDict.pop
        try:
            caduc.dicts.SyncDict.pop = mock.Mock(return_value = None)
            images.pop.when.called_with('some.key').should.return_value(None)

            image = mock.Mock()
            image.deleted = mock.Mock()
            caduc.dicts.SyncDict.pop = mock.Mock(return_value = image)
            images.pop.when.called_with('some.key').should.return_value(image)
            image.deleted.assert_called_once_with()
        finally:
            caduc.dicts.SyncDict.pop = pop


    def test_update_timers(self):
        images = self.getImages()
        img_mocks = {}
        for key in self.faker.pyiterable(10, True, str):
            img = mock.Mock()
            img.update_timer = mock.Mock()
            img_mocks[key] = img
        images.update(img_mocks)
        images.update_timers()
        for img in six.itervalues(img_mocks):
            img.update_timer.assert_called_once_with()
