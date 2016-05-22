import caduc.dicts
import docker.errors
import unittest
import sure

from .. import mock

class TestDicts(unittest.TestCase):

    def setUp(self):
        self.instanciate = caduc.dicts.SyncDict.instanciate
        self.list_items = caduc.dicts.SyncDict.list_items
        self.inspect = caduc.dicts.SyncDict.inspect
        self.getitem = caduc.dicts.SyncDict.__getitem__
        self.dockerErrorsNotFound = docker.errors.NotFound

    def tearDown(self):
        caduc.dicts.SyncDict.instanciate = self.instanciate
        caduc.dicts.SyncDict.list_items = self.list_items
        caduc.dicts.SyncDict.inspect = self.inspect
        caduc.dicts.SyncDict.__getitem__ = self.getitem
        self.unmockInstanciate()
        self.unmockList()
        self.unmockInspect()

    def mockList(self, items=[]):
        caduc.dicts.SyncDict.list_items = mock.Mock(return_value=items)
        return caduc.dicts.SyncDict.list_items

    def mockInstanciate(self, item=None):
        caduc.dicts.SyncDict.instanciate = mock.Mock(return_value=item)
        return caduc.dicts.SyncDict.instanciate

    def mockInspect(self, inspect=None, side_effect=None):
        caduc.dicts.SyncDict.inspect = mock.Mock(return_value=inspect, side_effect=side_effect)
        return caduc.dicts.SyncDict.inspect

    def unmockInstanciate(self):
        caduc.dicts.SyncDict.instanciate = self.instanciate

    def unmockList(self):
        caduc.dicts.SyncDict.list_items = self.list_items

    def unmockInspect(self):
        caduc.dicts.SyncDict.inspect = self.inspect

    def create_with_items(self, items = None, names={'my.name':'my.id'}):
        if items is None:
            items = {
                'my.id': {
                    'Id': 'my.id',
                },
            }
        self.mockList(items.values())
        self.mockInstanciate(mock.Mock())
        self.mockInspect(side_effect=lambda x: items[names.get(x,x)])
        return caduc.dicts.SyncDict()

    def test_init(self):
        self.mockList([dict(Id='some.id')])
        instance = mock.Mock()
        self.mockInstanciate(instance)
        self.mockInspect(inspect=dict(Id='some.id'))
        dct = caduc.dicts.SyncDict()
        dct['some.id'].should.be.eql(instance)
        caduc.dicts.SyncDict.instanciate.assert_called_once_with('some.id')
        caduc.dicts.SyncDict.list_items.assert_called_once_with()
        caduc.dicts.SyncDict.inspect.assert_called_with('some.id')

    def test_getitem_accepts_name_and_id(self):
        dct = self.create_with_items()
        caduc.dicts.SyncDict.instanciate.reset_mock()
        caduc.dicts.SyncDict.inspect.reset_mock()
        dct['my.id']
        caduc.dicts.SyncDict.instanciate.assert_not_called()
        caduc.dicts.SyncDict.inspect.assert_not_called()
        dct['my.name'].should.be(dct['my.id'])
        caduc.dicts.SyncDict.instanciate.assert_not_called()
        caduc.dicts.SyncDict.inspect.assert_called_once_with('my.name')

    def test_getitem_falls_back_to_instanciate(self):
        dct = self.create_with_items()
        def inspect(key):
            if key=='new.id':
                return dict(Id='new.id')
            raise KeyError
        caduc.dicts.SyncDict.inspect = mock.Mock(side_effect=inspect)
        instance = mock.Mock()
        caduc.dicts.SyncDict.instanciate = mock.Mock(return_value = instance)

        dct['new.id'].should.be(instance)
        caduc.dicts.SyncDict.inspect.assert_called_once_with('new.id')

    def test_getitem_raises_KeyError_when_not_exists(self):
        dct = self.create_with_items()
        docker.errors.NotFound = Exception
        caduc.dicts.SyncDict.inspect.side_effect = docker.errors.NotFound
        dct.__getitem__.when.called_with('non.existing').should.throw(docker.errors.NotFound)

    def test_pop_accepts_name_and_id(self):
        dct = self.create_with_items()
        caduc.dicts.SyncDict.instanciate.reset_mock()
        caduc.dicts.SyncDict.inspect.reset_mock()
        dct.pop('my.id')
        dct.should_not.contain('my.id')
        caduc.dicts.SyncDict.instanciate.assert_not_called()
        caduc.dicts.SyncDict.inspect.assert_not_called()
        dct.should.be.empty

        dct = self.create_with_items()
        caduc.dicts.SyncDict.instanciate.reset_mock()
        caduc.dicts.SyncDict.inspect.reset_mock()
        dct.pop('my.name')
        dct.should_not.contain('my.id')
        caduc.dicts.SyncDict.instanciate.assert_not_called()
        caduc.dicts.SyncDict.inspect.assert_called_once_with('my.name')

    def test_pop_returns_default_when_unknown_key(self):
        dct = self.create_with_items()
        caduc.dicts.SyncDict.instanciate.reset_mock()
        caduc.dicts.SyncDict.inspect.reset_mock()
        dct.pop.when.called_with('missing.id').should.return_value(None)
        caduc.dicts.SyncDict.instanciate.assert_not_called()
        caduc.dicts.SyncDict.inspect.assert_called_once_with('missing.id')

        caduc.dicts.SyncDict.inspect = mock.Mock(return_value=dict(Id='missing.id'))
        dct.pop.when.called_with('missing.id').should.return_value(None)

    def test_setitem(self):
        dct = self.create_with_items()
        caduc.dicts.SyncDict.inspect = mock.Mock(return_value=dict(Id='new.id'))
        item = mock.Mock()
        dct['new.id'] = item
        dct['new.id'].should.be(item)
        
        dct = self.create_with_items()
        caduc.dicts.SyncDict.inspect = mock.Mock(return_value=dict(Id='new.id'))
        item = mock.Mock()
        dct['new.name'] = item
        dct['new.id'].should.be(item)

    def test_setitem_fails_to_override_value(self):
        dct = self.create_with_items()
        caduc.dicts.SyncDict.inspect = mock.Mock(return_value=dict(Id='my.id'))
        item = mock.Mock()
        dct.__setitem__.when.called_with('new.name', item).should.throw(KeyError)
        dct['my.id'].should_not.be(item)

    def test_delitem_accepts_name_and_id(self):
        dct = self.create_with_items()
        caduc.dicts.SyncDict.instanciate.reset_mock()
        caduc.dicts.SyncDict.inspect.reset_mock()
        del dct['my.id']
        dct.should_not.contain('my.id')
        caduc.dicts.SyncDict.instanciate.assert_not_called()
        caduc.dicts.SyncDict.inspect.assert_not_called()
        dct.should.be.empty

        dct = self.create_with_items()
        caduc.dicts.SyncDict.instanciate.reset_mock()
        caduc.dicts.SyncDict.inspect.reset_mock()
        del dct['my.name']
        dct.should_not.contain('my.id')
        caduc.dicts.SyncDict.instanciate.assert_not_called()
        caduc.dicts.SyncDict.inspect.assert_called_once_with('my.name')

    def test_delitem_raises_KeyError_when_unknown_key(self):
        dct = self.create_with_items()
        caduc.dicts.SyncDict.instanciate.reset_mock()
        caduc.dicts.SyncDict.inspect = mock.Mock(return_value=dict(Id='missing.del.id'))
        dct.__delitem__.when.called_with('missing.del.id').should.throw(KeyError)
        caduc.dicts.SyncDict.instanciate.assert_not_called()
        caduc.dicts.SyncDict.inspect.assert_called_once_with('missing.del.id')

    def test_add(self):
        caduc.dicts.SyncDict.__getitem__ = mock.Mock()
        dct = self.create_with_items()
        dct.__getitem__.reset_mock()
        dct.add('some.item')
        dct.__getitem__.assert_called_once_with('some.item')

    def test_class_must_be_inherited(self):
        dct = self.create_with_items()
        self.unmockInstanciate()
        self.unmockList()
        self.unmockInspect()
        dct.instanciate.when.called_with(mock.ANY).should.throw(NotImplementedError)
        dct.list_items.when.called_with().should.throw(NotImplementedError)
        dct.inspect.when.called_with().should.throw(NotImplementedError)

