import os
import yaml

class Node(dict):

    def __init__(self, **values):
        super(Node, self).__init__()
        self.update(values)

    def update(self, other):
        for k, v in other.iteritems():
            try:
                node = self[k]
            except KeyError:
                node = Node()
                self[k] = node
            if isinstance(v, dict):
                if not isinstance(node, dict):
                    raise ValueError("Can't update uncoherent values for key %s, old value: %r, new value: %r" % (k, node, v))
                node.update(v)
            else:
                self[k] = v

class Config(Node):

    def __init__(self, options, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.expanduser("~"), ".caduc", "config.yml")
        if os.path.exists(config_path):
            config = yaml.load(file(config_path, 'r'))
        else:
            config = {}
        for opt in options:
            k, v = self.parse_kv(opt)
            node = config
            keys = self.parse_key(k)
            for key in keys[:-1]:
                try:
                    node = config[key]
                except KeyError:
                    node = {}
                    config[key] = node
            node[key[-1]] = v
        super(Config, self).__init__(**config)

    def parse_key(self, key):
        return key.split('.', 1)

    def parse_kv(self, kv):
        return kv.split('=', 1)

    def get(self, path, default=None):
        node = self
        try:
            for key in self.parse_key(path):
                node = node[key]
            return node
        except KeyError:
            return default

