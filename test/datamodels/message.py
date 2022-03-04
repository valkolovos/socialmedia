from socialmedia.models import Message as BaseMessage

from .base import BaseTestModel

class Message(BaseMessage, BaseTestModel):
    pass
