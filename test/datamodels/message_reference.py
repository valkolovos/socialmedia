from socialmedia.models import MessageReference as BaseMessageReference

from .base import BaseTestModel

class MessageReference(BaseMessageReference, BaseTestModel):
    pass

