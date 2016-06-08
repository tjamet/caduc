import os
import six
import yaml

class Node(dict):

    def __init__(self, **values):
        super(Node, self).__init__()
        self.update(values)

    def update(self, other):
        for k, v in six.iteritems(other):
            try:
                oldv = self[k]
            except KeyError:
                if isinstance(v, dict):
                    node = Node()
                    node.update(v)
                    self[k] = node
                else:
                    self[k] = v
            else:
                if isinstance(oldv, dict):
                    if not isinstance(v, dict):
                        raise ValueError("Can't update uncoherent values for key %s, old value: %r, new value: %r" % (k, oldv, v))
                    oldv.update(v)
                else:
                    if isinstance(v, dict):
                        raise ValueError("Can't update uncoherent values for key %s, old value: %r, new value: %r" % (k, oldv, v))
                    self[k] = v

class Config(Node):

    def __init__(self, options=[], config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.expanduser("~"), ".caduc", "config.yml")
            if os.path.exists(config_path):
                config = yaml.load(open(config_path, 'r'))
            else:
                config = {}
        else:
            config = yaml.load(open(config_path, 'r'))
        super(Config, self).__init__(**config)
        for opt in options:
            k, v = self.parse_kv(opt)
            node = {}
            child = node
            keys = self.parse_key(k)
            for key in keys[:-1]:
                child[key] = {}
                child = child[key]
            child[keys[-1]] = v
            self.update(node)

    def parse_key(self, key):
        r = key.split('.')
        if r == ['']:
            raise ValueError('Failed to find any key in %r' % key)
        return r

    def parse_kv(self, kv):
        r = kv.split('=', 1)
        if len(r) != 2:
            raise ValueError('Failed to decode <key>=<value> in %r.' % kv)
        return r

    def get(self, path, default=None):
        node = self
        try:
            for key in self.parse_key(path):
                node = node[key]
            return node
        except KeyError:
            return default

