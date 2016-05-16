from .container import Container
from .dicts import SyncDict

class Containers(SyncDict):
    AttributeName = 'container'
    def __init__(self, config, client, images):
        self.config = config
        self.client = client
        self.images = images
        super(Containers, self).__init__()

    def instanciate(self, item):
        container = Container(self.config, self.client, item)
        try:
            self.images[container.image_id].add(container)
        except KeyError:
            self.logger.error("%s is running on not found image %s. It looks like it has been deleted --force" % (container, container.image_id))
        return container

    def inspect(self, *args, **kwds):
        return self.client.inspect_container(*args, **kwds)

    def list_items(self):
        return self.client.containers(all=True)

    def pop(self, container):
        container = super(Containers, self).pop(container)
        self.logger.info("container %s was removed", container)
        try:
            self.images[container.image_id].remove(container)
        except KeyError:
            self.logger.error("%s is running on not found image %s. It looks like it has been deleted --force" % (container, container.image_id))
        return container

