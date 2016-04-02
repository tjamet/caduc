import docker
import logging

class SyncDict(dict):
    """
        A key->value class with:
            - alias/names transation to client ids (reference any image/container name/id returns the same objects)
            - cache miss retrieval from client when it exists
            - automatic initialization with client contents
    """
    AttributeName = None

    def instanciate(self, Id):
        """
            implement this method to create the object to be created when a new item is found in the client
            Must return the instance of the object corresponding to the 'Id'
        """
        raise NotImplementedError("Please implement instanciate(Id)")

    def list_items(self):
        """
            implement this method, listing all available Ids in the client
            Must return an iterable over Ids (string)
        """
        raise NotImplementedError("Please implement list_items()")

    def inspect(self, *args, **kwds):
        """
            implement this method, retrieving key->value concerning item attributes
            Must return a dict with an 'Id' key
            Should raise KeyError if no item can be retrieved
            Must return None when no item can be retrieved and no exception was thrown
        """
        raise NotImplementedError("Please implement inspect(*args, **kwds)")

    def __init__(self):
        self.logger = logging.getLogger(str(self.__class__))
        super(SyncDict, self).__init__()
        for item in self.list_items():
            self.logger.debug("id: %s ", item['Id'])
            self.add(item['Id'])

    def __inspect(self, item):
        try:
            if isinstance(item, (tuple, list)):
                return self.inspect(*item)
            else:
                return self.inspect(item)
        except docker.errors.NotFound:
            raise KeyError("Failed to retrieve %s matching '%r'" % (self.AttributeName, item))

    def __iterItemIds(self, item):
        """
            A method for key lookup.
            First try the exact same key, and fallback calling the client when not found
        """
        yield item
        yield self.__inspect(item)['Id']

    def __getitem__(self, item):
        """
            Gets a key and fall back instanciating one when not available
        """
        for id in self.__iterItemIds(item):
            try:
                self.logger.debug("getting item %s", id)
                return super(SyncDict, self).__getitem__(id)
            except KeyError:
                continue
        self.logger.debug("Failed to retrieve %s from cache, instanciate one", item)
        instance = self.instanciate(id)
        if instance is not None:
            super(SyncDict, self).__setitem__(id, instance)
        return super(SyncDict, self).__getitem__(id)

    def pop(self, item):
        for id in self.__iterItemIds(item):
            try:
                self.logger.debug("popping item %s keys %s", id, self.keys())
                return super(SyncDict, self).__getitem__(id)
            except KeyError:
                continue
        raise KeyError("%s: no such key", item)

    def __setitem__(self, item, value):
        """
            Stores a new item, raises KeyError if the key already exists
        """
        inspect = self.__inspect(item)
        if inspect['Id'] in self.keys():
            raise KeyError("Cannot overwrite an %s" % self.AttributeName)
        return super(SyncDict, self).__setitem__(inspect['Id'], value)

    def __delitem__(self, item):
        try:
            inspect = self.__inspect(item)
            id = inspect['Id']
        except KeyError:
            id = item
        super(SyncDict, self).__delitem__(id)

    def add(self, item):
        """
            Automatic value creation
            retrieves item Id and call instanciate(item)
        """
        inspect = self.__inspect(item)
        try:
            self[item]
        except KeyError:
            self.logger.debug("Adding item %s", item)
            return super(SyncDict, self).__setitem__(inspect['Id'], self.instanciate(inspect['Id']))

