import docker
import fnmatch
import logging
import pytimeparse.timeparse
import threading

from .timer import Timer

DEFAULT_DELETE_TIMEOUT = "1d"

class ClientSemaphore(object):
    def __init__(self, count=5):
        self.semaphore = threading.Semaphore(count)
    def __enter__(self):
        self.semaphore.acquire()
        return self
    def __exit__(self, *args,**kwds):
        self.semaphore.release()

class Image(set):
    DefaultTimeout = DEFAULT_DELETE_TIMEOUT
    # allow max 5 concurrent deletes, preventing from requests.packages.urllib3.connectionpool:Connection pool is full, discarding connection errors
    RmSemaphore = ClientSemaphore(5)
    Timer = Timer

    def timeparse(self, *args, **kwds):
        return pytimeparse.timeparse.timeparse(*args, **kwds)

    def __init__(self, config, images, client, Id, default_timeout=None):
        self.config = config
        self.logger = logging.getLogger(str(self.__class__))
        self.event = None
        self.client = client
        self.images = images
        self.grace_time = self.DefaultTimeout if default_timeout is None else default_timeout
        self.details = self.client.inspect_image(Id)
        self.id = self.details['Id']

        self.children = set()
        parentId = self.details.get('Parent', None)
        # drop empty strings, consider them as None
        self.parentId = parentId if parentId else None
        if self.parentId:
            self.images[parentId].add_child(self.id)
        super(Image, self).__init__()
    
    def __hash__(self):
        return hash(self.id)

    def get_grace_times(self, names):
        labels = self.details['Config']['Labels']
        if labels and labels.get("com.caduc.image.grace_time"):
            return set([labels.get('com.caduc.image.grace_time', None)])
        grace_config = self.config.get("images")
        grace_times = set()
        if grace_config:
            for name in names:
                for pattern, kv in grace_config.iteritems():
                    if fnmatch.fnmatch(name, pattern):
                        grace_time = kv['grace_time']
                        if grace_time is None or grace_time==-1:
                            grace_times.add(float('inf'))
                        else:
                            grace_times.add(kv['grace_time'])
        if grace_times:
            return grace_times
        if self.grace_time:
            return [ self.grace_time ]
        return [ self.DefaultTimeout ]

    def parse_grace_time(self, timeout):
        if isinstance(timeout, (str, unicode)):
            seconds = self.timeparse(timeout)
            if seconds is None:
                seconds = int(timeout)
        else:
            seconds = timeout
        return seconds

    def refresh(self):
        self.details = self.client.inspect_image(self.id)
        self.update_timer()

    def __str__(self):
        return 'Image<Id: %s, names: %r parent: %s, children: %r>' % (self.details['Id'], self.details.get('RepoTags', None), self.parentId, self.children)

    def __rm__(self):
        self.deleted()
        super(Image, self).__rm__()

    def deleted(self):
        self.cancel_rm()
        if self.parentId:
            self.images[self.parentId].delete_child(self.id)

    def add_child(self, child):
        self.logger.debug("%s inherits %s", child, self)
        self.children.add(child)
        self.update_timer()

    def delete_child(self, child):
        self.logger.debug("%s sub image was deleted %s", self, child)
        self.children.remove(child)
        self.update_timer()
 
    def schedule_rm(self):
        grace_texts = self.get_grace_times(self.details['RepoTags'])
        seconds = -1
        grace_text = None
        for txt in grace_texts:
            t = self.parse_grace_time(txt)
            if t > seconds:
                seconds = t
                grace_text = txt
        if seconds<0 or seconds==float('inf'):
            self.logger.debug("not scheduling %s removal, delete delay %r is negative or infinite", self, seconds)
            return
        if not self.event:
            self.logger.info("scheduling %s removal in %s (%r s)", self, grace_text, seconds)
            self.event = self.Timer(seconds, self.rm)
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
        with self.RmSemaphore:
            # we are about to request an image deletion
            # cancel the original timer and schedule another one in case the deletion fails
            self.cancel_rm()
            self.logger.info("deleting image %s", self)
            for name in self.details.get('RepoTags', []) + [self.id]:
                try:
                    self.client.remove_image(name)
                except docker.errors.NotFound:  
                    try:
                        self.refresh()
                        if not self.event:
                            break
                    except docker.errors.NotFound:
                        self.images.pop(self.id)
                        break
                except Exception as e:
                    self.logger.error("Failed removing %s exception raised: %s" % (self, e))
                    break
            else:
                self.logger.debug("Failed to delete %s, give it another chance", self)
                self.schedule_rm()
            # while we don't have the acknoledgement through
            # the event callback, keep the image reference in memory

