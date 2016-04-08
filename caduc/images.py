from .image import Image
from .dicts import SyncDict

class Images(SyncDict):
    AttributeName = 'image'
    def __init__(self, config, client, default_timeout=None):
        self.client = client
        self.config = config
        self.default_timeout = default_timeout
        super(Images, self).__init__()

    def instanciate(self, item):
        return Image(self.config, self, self.client, item, self.default_timeout)

    def inspect(self, *args, **kwds):
        return self.client.inspect_image(*args, **kwds)

    def list_items(self):
        return self.client.images(all=True)

    def pop(self, image):
        image = super(Images, self).pop(image)
        if image is not None:
            self.logger.info("image %s was removed", image)
            image.deleted()
        return image

    def update_timers(self):
        for image in self.itervalues():
            image.update_timer()

