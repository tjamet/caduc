from .container import Container
from .dicts import SyncDict

class Containers(SyncDict):
    AttributeName = 'container'
    def __init__(self, client, images):
        self.client = client
        self.images = images
        super(Containers, self).__init__()

    def instanciate(self, item):
        container = Container(self.client, item)
        self.images[container.image_id].add(container)
        return container

    def inspect(self, *args, **kwds):
        return self.client.inspect_container(*args, **kwds)

    def list_items(self):
        return self.client.containers()

    def pop(self, container):
        container = super(Containers, self).pop(container)
        self.logger.info("container %s was removed", container)
        self.images[container.image_id].remove(container)
        return container

