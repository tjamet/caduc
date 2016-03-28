import logging

from pytimeparse.timeparse import timeparse
from .timer import Timer

DEFAULT_DELETE_TIMEOUT = "1d"

class Image(set):
    DefaultTimeout = DEFAULT_DELETE_TIMEOUT

    def __init__(self, images, client, Id, default_timeout=None):
        self.logger = logging.getLogger(str(self.__class__))
        self.event = None
        self.client = client
        self.images = images
        self.delete_timeout = self.DefaultTimeout if default_timeout is None else default_timeout
        self.id = self.client.inspect_image(Id)['Id']
        self.children = set()
        self.refresh(False)
        parentId = self.details.get('Parent', None)
        self.parent = self.images[parentId] if parentId else None
        if self.parent:
            self.parent.add_child(self)
        super(Image, self).__init__()
    
    def __hash__(self):
        return hash(self.id)

    def refresh(self, update_timer=True):
        self.details = self.client.inspect_image(self.id)
        labels = self.details['Config']['Labels']
        delete_timeout = labels.get('com.cddc.image.grace_time', None) if labels else None
        if delete_timeout is not None:
            self.delete_timeout = delete_timeout
        if update_timer:
            self.update_timer()

    def __str__(self):
        return 'Image<Id: %s, names: %r>' % (self.details['Id'], self.details.get('RepoTags', None))

    def __rm__(self):
        self.cancel_rm()
        if self.parent:
            self.parent.delete_child(self)
        super(Image, self).__rm__()

    def add_child(self, child):
        self.logger.debug("%s inherits %s", child, self)
        self.children.add(child)
        self.update_timer()

    def delete_child(self, child):
        self.logger.info("%s sub image was deleted %s", self, child)
        self.children.remove(child)
        self.update_timer()
 
    def schedule_rm(self):
        if self.delete_timeout is not None:
            delete_timeout = self.delete_timeout
        else:
            delete_timeout = self.DefaultTimeout
        if isinstance(delete_timeout, (str, unicode)):
            seconds = timeparse(delete_timeout)
            if seconds is None:
                seconds = int(delete_timeout)
        else:
            seconds = delete_timeout
        if seconds<0:
            self.logger.info("not scheduling %s removal, delete delay %r is negative", self, seconds)
            return
        if not self.event:
            self.logger.info("scheduling %s removal in %s (%r s)", self, delete_timeout, seconds)
            self.event = Timer(seconds, self.rm)
            self.event.start()

    def cancel_rm(self):
        if self.event is not None:
            self.logger.info("cancelling %s removal", self)
            self.event.cancel()
        self.event = None

    def update_timer(self):
        if not self and not self.children:
            self.schedule_rm()
        else:
            self.cancel_rm()

    def add(self, container):
        self.logger.debug("%s is required to run %s", self, container)
        super(Image, self).add(container)
        self.update_timer()

    def remove(self, container):
        super(Image, self).remove(container)
        self.update_timer()

    def rm(self):
        self.logger.info("deleting old image %s", self)
        self.client.remove_image(self.id)
        # while we don't have the acknoledgement through
        # the event callback, keep the image reference in memory

