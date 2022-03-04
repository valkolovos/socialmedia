class BaseTestModel():
    _data = []

    @classmethod
    def add_data(cls, data):
        cls._data.append(data)

    @classmethod
    def get(cls, **kwargs):
        for e in cls._data:
            if type(e) != cls:
                continue
            matched = True
            for k, v in kwargs.items():
                if not hasattr(e, k) or not getattr(e,k) == v:
                    matched = False
            if matched:
                return e

    @classmethod
    def list(cls, **kwargs):
        response = []
        for e in cls._data:
            if type(e) != cls:
                continue
            matched = True
            if 'order' in kwargs:
                del kwargs['order']
            for k, v in kwargs.items():
                if not hasattr(e, k) or not getattr(e,k) == v:
                    matched = False
            if matched:
                response.append(e)
        return response

    def save(self):
        self.__class__.add_data(self)

    def delete(self):
        delIdx = None
        for idx, e in enumerate(self.__class__._data):
            if e == self:
                delIdx = idx
        if delIdx is not None:
            del self.__class__._data[delIdx]
