import docker
import logging

class Watcher(object):

    def __init__(self, client, images, containers):
        self.logger = logging.getLogger(str(self.__class__))
        self.client = client
        self.images = images
        self.containers = containers

    def tag(self, event):
        self.images[event['id']].refresh()
    
    def untag(self, event):
        try:
            self.images[event['id']].refresh()
        except KeyError:
            self.logger.debug("%s was deleted before handling event", event['id'])
        except docker.errors.NotFound:
            self.images.pop(event['id'])

    def commit(self, event):
        self.logger.debug("would re-load image list for event %r", event)

    def delete(self, event):
        try:
            self.images.pop(event['id'])
        except KeyError:
            self.logger.error("Failed to destroy image %s, it was expected to be already deleted", event['id'])

    def create(self, event):
        self.containers.add(event['id'])

    def destroy(self, event):
        try:
            self.containers.pop(event['id'])
        except KeyError:
            self.logger.error("Failed to destroy container %s, it was expected to be already deleted", event['id'])

    def __noop(self, event):
        self.logger.debug("no op %r", event)

    def watch(self):
        for event in self.client.events(decode=True):
            try:
                getattr(self, event['Action'], self.__noop)(event)
            except Exception as e:
                self.logger.error("Failed to handle event %r, error: %r" % (event, e))

