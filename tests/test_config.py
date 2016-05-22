import caduc.config
import faker
import mock
import os
import random
import sure
import unittest
import yaml


class TestNode(unittest.TestCase):

    def setUp(self):
        self.faker = faker.Faker()

    def test_init_empty(self):
        node = caduc.config.Node()
        node.should.be.empty

    def test_init_with_values(self):
        value = self.faker.text()
        node = caduc.config.Node(someAttribute=value)
        dict(node).should.be.eql({'someAttribute':value})

        dic = self.faker.pydict(nb_elements=10, variable_nb_elements=True)
        node = caduc.config.Node(**dic)
        for key, val in node.iteritems():
            val.should.be.eql(dic[key])
        dict(node).should.be.eql(dic)

        # ensure Node initializer does not alter source dict
        dic = self.faker.pydict(nb_elements=10, variable_nb_elements=True)
        orig = dict(dic)
        caduc.config.Node(**dic)
        dic.should.be.eql(orig)

    def test_flat_update(self):
        base = self.faker.pydict(nb_elements=10, variable_nb_elements=True)
        update = self.faker.pydict(nb_elements=10, variable_nb_elements=True)
        _base = dict(base)
        _update = dict(update)
        merged = dict(base)
        merged.update(update)

        baseNode = caduc.config.Node(**base)
        updateNode = caduc.config.Node(**update)

        baseNode.update(update)
        # ensure Node update did not alter source
        # dicts
        base.should.eql(_base)
        update.should.eql(_update)
        dict(baseNode).should.eql(merged)

        baseNode = caduc.config.Node(**base)
        baseNode.update(updateNode)
        # ensure Node update did not alter source
        # dicts
        base.should.eql(_base)
        update.should.eql(_update)
        dict(updateNode).should.eql(_update)
        baseNode.should.eql(caduc.config.Node(**merged))

        baseNode = caduc.config.Node(**base)
        for value in [
            self.faker.text(),
            self.faker.pystr(),
            self.faker.pyint(),
            self.faker.pylist(),
            self.faker.pyset(),
            ]:
                key = random.choice(base.keys())
                baseNode.update({key: value})
                baseNode[key].should.eql(value)


    def test_struct_update(self):
        node = caduc.config.Node(key1= {'subkey1': 'value 1'})
        node.update({'key1': {'subkey2': 'value 2'}})
        dict(node).should.be.eql({
            'key1':{
                'subkey1': 'value 1',
                'subkey2': 'value 2',
            }
       })

    def test_struct_override(self):
        dic = {
            'key1': 'string',
            'key2': {'subKey2': 'string'}
        }
        node = caduc.config.Node(**dic)
        with self.assertRaises(ValueError):
            node.update({'key1': {'subkey1': 'string'}})
        with self.assertRaises(ValueError):
            node.update({'key2': 'string'})


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.orig_osp = {}
    def tearDown(self):
        for key, val in self.orig_osp.iteritems():
            setattr(os.path, key, val)

    def stub_config(self, homedir='HOME', ospjoin='.', exists=False):
        for key, mocked in (
                ['expanduser', homedir],
                ['join', ospjoin],
                ['exists', exists],
            ):
            self.orig_osp[key] = getattr(os.path, key)
            setattr(os.path, key, mock.MagicMock(return_value=mocked))

    @property
    def config_path(self):
        return 'tests/fixtures/config.yml'

    @property
    def config_dict(self):
        return yaml.load(open(self.config_path))

    def test_init_default_path(self):
        self.stub_config('HOME', '.', False)
        caduc.config.Config([])
        os.path.expanduser.assert_called_once_with('~')
        os.path.join.assert_called_once_with('HOME', '.caduc', 'config.yml')
        os.path.exists.assert_called_once_with('.')

    def test_init_no_arg(self):
        self.stub_config('HOME', '.', False)
        caduc.config.Config()
        os.path.expanduser.assert_called_once_with('~')
        os.path.join.assert_called_once_with('HOME', '.caduc', 'config.yml')
        os.path.exists.assert_called_once_with('.')

    def test_init_named_args(self):

        self.stub_config()
        cfg = caduc.config.Config(config_path=self.config_path)
        dict(cfg).should.be.eql(self.config_dict)

        os.path.expanduser.assert_not_called()
        os.path.join.assert_not_called()
        os.path.exists.assert_not_called()


    def test_init_empty_config(self):
        self.stub_config(exists=False)
        caduc.config.Config([]).should.be.empty

    def test_init_load_yaml(self):
        self.stub_config(ospjoin=self.config_path, exists=True)
        cfg = caduc.config.Config([])
        dict(cfg).should.be.eql(self.config_dict)

        self.stub_config(exists=False)
        cfg = caduc.config.Config([], self.config_path)
        dict(cfg).should.be.eql(self.config_dict)


    def test_parse_key(self):
        self.stub_config()
        cfg = caduc.config.Config()
        cfg.parse_key.when.called_with(
            'some.long.key.with.dots'
        ).should.return_value(
            ['some', 'long', 'key', 'with', 'dots']
        )

    def test_parse_kv(self):
        self.stub_config()
        cfg = caduc.config.Config()
        cfg.parse_kv.when.called_with(
            'some.long.key.with.dots=value'
        ).should.return_value(
            ['some.long.key.with.dots', 'value']
        )
        cfg.parse_kv.when.called_with(
            'some.long.key.with.dots=value=with='
        ).should.return_value(
            ['some.long.key.with.dots', 'value=with=']
        )

    def test_parse_options(self):
        self.stub_config()
        cfg = caduc.config.Config(['some.key=2'])
        dict(cfg).should.eql({
            'some': {
                'key': '2',
            }
        })

        cfg = caduc.config.Config(['some.other.key=2'])
        dict(cfg).should.eql({
            'some': {
                'other':{
                    'key': '2',
                }
            }
        })

        cfg = caduc.config.Config(['some.other.key=2', 'some.other.key=5'])
        dict(cfg).should.eql({
            'some': {
                'other':{
                    'key': '5',
                }
            }
        })

        cfg = caduc.config.Config(['some.other.key=2', 'some.other.key2=5'])
        dict(cfg).should.eql({
            'some': {
                'other':{
                    'key': '2',
                    'key2': '5',
                }
            }
        })

        with self.assertRaises(ValueError):
            cfg = caduc.config.Config(['1'])
        with self.assertRaises(ValueError):
            cfg = caduc.config.Config(['=1'])

    def test_get_single_key(self):
        cfg = caduc.config.Config(['some.key=2', 'somevalue=1'])
        cfg.get.when.called_with('somevalue').should.return_value('1')
        cfg.get.when.called_with('somevalue', None).should.return_value('1')
        cfg.get.when.called_with('some.key').should.return_value('2')
        cfg.get.when.called_with('some.key', None).should.return_value('2')

    def test_get_key_returns_default_value_on_miss(self):
        cfg = caduc.config.Config(['some.key=2', 'somevalue=1'])
        cfg.get.when.called_with('some.other.key').should.return_value(None)
        cfg.get.when.called_with('some.other.key', 'some.default').should.return_value('some.default')
        

