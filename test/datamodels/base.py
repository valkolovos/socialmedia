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
            # if no kwargs passed in and type matches, we're good
            matched = len(kwargs.items()) == 0
            for k, v in kwargs.items():
                if hasattr(e, k) and getattr(e,k) == v:
                    matched = True
                elif isinstance(v, BaseTestModel):
                    # check if child BaseTestModel objects have the expected value
                    obj_attrs = [attr for attr in dir(e) if not attr.startswith('_')]
                    for attr_name in obj_attrs:
                        if (
                            isinstance(getattr(e, attr_name), BaseTestModel) and
                            hasattr(getattr(e, attr_name), k) and
                            getattr(getattr(e, attr_name), k) == v
                        ):
                            matched = True
                            continue
                else:
                    matched = False
            if matched:
                return e

    @classmethod
    def list(cls, **kwargs):
        response = []
        for e in cls._data:
            if type(e) != cls:
                continue
            if 'order' in kwargs:
                del kwargs['order']
            matched = len(kwargs.items()) == 0
            for k, v in kwargs.items():
                if hasattr(e, k) and getattr(e,k) == v:
                    matched = True
                elif isinstance(v, BaseTestModel):
                    # check if child BaseTestModel objects have the expected value
                    obj_attrs = [attr for attr in dir(e) if not attr.startswith('_')]
                    for attr_name in obj_attrs:
                        if (
                            isinstance(getattr(e, attr_name), BaseTestModel) and
                            hasattr(getattr(e, attr_name), k) and
                            getattr(getattr(e, attr_name), k) == v
                        ):
                            matched = True
                            continue
                else:
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
