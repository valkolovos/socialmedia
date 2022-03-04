from socialmedia.models import Connection as BaseConnection

from .base import BaseTestModel

class Connection(BaseConnection, BaseTestModel):
    pass
