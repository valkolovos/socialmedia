from .dataclient import datastore_client

class DatastoreBase:
    def save(self):
        """ save method to implement """

    def as_dict(self):
        """ method to implement that returns object as dictionary """

    def delete(self):
        if hasattr(self, 'key'):
            datastore_client.delete(getattr(self, 'key'))

    @classmethod
    def get(cls, **kwargs):
        '''
        executes a search using provided keywords and returns
        the first one foud if any
        '''
        query = datastore_client.query(kind=cls.kind)
        for key, value in kwargs.items():
            if isinstance(value, DatastoreBase) and hasattr(value, 'key'):
                query.ancestor=getattr(value, 'key')
            else:
                query.add_filter(key, '=', value)
        results = list(query.fetch(limit=1))
        if results:
            return cls._build_obj(results[0])
        return None

    @classmethod
    def list(cls, **kwargs):
        '''
        executes a search using provided keywords
        if 'order' exists in kwargs, the value will be used as sort
        '''
        query = datastore_client.query(kind=cls.kind)
        kwarg_objects = {key: value for (key, value) in kwargs.items() if isinstance(value, DatastoreBase)}
        if 'order' in kwargs:
            query.order = kwargs.pop('order')
        for key, value in kwargs.items():
            if isinstance(value, DatastoreBase) and hasattr(value, 'key'):
                query.ancestor=getattr(value, 'key')
            else:
                query.add_filter(key, '=', value)
        results = [cls._build_obj(i) for i in list(query.fetch())]
        for key, value in kwarg_objects.items():
            for result in results:
                if hasattr(result, key):
                    setattr(result, key, value)
        return results

    @classmethod
    def _build_obj(cls, datastore_obj):
        obj = cls.__new__(cls)
        obj.__init__(
            **dict(datastore_obj.items())
        )
        setattr(obj, 'key', datastore_obj.key)
        if hasattr(obj, 'from_datastore_obj'):
            obj.from_datastore_obj(datastore_obj)
        return obj
