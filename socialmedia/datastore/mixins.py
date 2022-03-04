from .dataclient import datastore_client

class DatastoreBase:
    def save(self):
        """ save method to implement """

    def set_datastore_id(self, datastore_id):
        self.datastore_id = datastore_id

    def set_key(self, key):
        self.key = key

    def as_dict(self):
        """ method to implement that returns object as dictionary """

    def delete(self):
        datastore_client.delete(self.key)

class DatastoreGetMixin:

    @classmethod
    def get(cls, **kwargs):
        '''
        executes a search using provided keywords and returns
        the first one foud if any
        '''
        query = datastore_client.query(kind=cls.kind)
        for k, v in kwargs.items():
            if isinstance(v, DatastoreBase):
                query.ancestor=v.key
            else:
                query.add_filter(k, '=', v)
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
        kwarg_objects = dict([(k,v) for k,v in kwargs.items() if isinstance(v, DatastoreBase)])
        if 'order' in kwargs:
            query.order = kwargs.pop('order')
        for k, v in kwargs.items():
            if isinstance(v, DatastoreBase):
                query.ancestor=v.key
            else:
                query.add_filter(k, '=', v)
        results = [cls._build_obj(i) for i in list(query.fetch())]
        for k, v in kwarg_objects.items():
            for result in results:
                if hasattr(result, k):
                    setattr(result, k, v)
        return results

    @classmethod
    def get_by_id(cls, obj_id, parent=None):
        '''
        retrieves the object using its primary key
        '''
        if not parent:
            key = datastore_client.key(cls.kind, obj_id)
        else:
            key = datastore_client.key(parent.__class__.kind, parent.datastore_id, cls.kind, obj_id)
        datastore_obj = datastore_client.get(key)
        if datastore_obj:
            return cls._build_obj(datastore_obj)
        return None

    @classmethod
    def _build_obj(cls, datastore_obj):
        obj = cls.__new__(cls)
        obj.__init__(
            **dict(datastore_obj.items())
        )
        obj.set_datastore_id(datastore_obj.id)
        obj.set_key(datastore_obj.key)
        if hasattr(obj, 'from_datastore_obj'):
            obj.from_datastore_obj(datastore_obj)
        return obj
