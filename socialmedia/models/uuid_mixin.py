from uuid import uuid4

class UuidMixin():

    @classmethod
    def generate_uuid(cls):
        return str(uuid4())
