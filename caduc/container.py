import logging

class Container(set):
    def __init__(self, config, client, id):
        self.config = config
        self.logger = logging.getLogger(str(self.__class__))
        self.client = client
        inspect = self.client.inspect_container(id)
        self.name = inspect.get('Name', None)
        self.id = inspect['Id']
        self.image_id = inspect['Image']
    def __hash__(self):
        return hash(self.id)
    def __str__(self):
        return 'Container<id: %s, name:%s>' % (self.id, self.name)

