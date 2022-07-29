from datetime import datetime

from Crypto import Random
from Crypto.PublicKey import RSA
from dateutil import tz

class Profile():
    def __init__(self, **kwargs):
        now = datetime.now().astimezone(tz.UTC)
        self.display_name = kwargs.get('display_name')
        self.handle = kwargs.get('handle')
        self.user_id = kwargs.get('user_id')
        self.image = kwargs.get('image')
        self.cover_image = kwargs.get('cover_image')
        self.public_key = kwargs.get('public_key')
        self.private_key = kwargs.get('private_key')
        self.created = kwargs.get('created', now)
        if not any((self.public_key, self.private_key)):
            self.public_key, self.private_key = self.generate_keys()

    @classmethod
    def generate_keys(cls):
        random_generator = Random.new().read
        crypto_key = RSA.generate(2048, random_generator)
        return crypto_key.publickey().exportKey(), crypto_key.exportKey()

    def __str__(self):
        return f'display_name: {self.display_name}, handle: {self.handle}, user_id: {self.user_id}, ' \
            f'image: {self.image}, cover_image: {self.cover_image}, created: {self.created}'

    def __repr__(self):
        return f'Profile(display_name: {self.display_name}, handle: {self.handle}, user_id: {self.user_id}, ' \
            f'image: {self.image}, cover_image: {self.cover_image}, public_key: {self.public_key}, created: {self.created})'

    def __eq__(self, other):
        return all([
            isinstance(other, self.__class__),
            hasattr(other, 'display_name') and self.display_name == other.display_name,
            hasattr(other, 'handle') and self.handle == other.handle,
            hasattr(other, 'user_id') and self.user_id == other.user_id,
            hasattr(other, 'image') and self.image == other.image,
            hasattr(other, 'cover_image') and self.cover_image == other.cover_image,
            hasattr(other, 'public_key') and self.public_key == other.public_key,
            hasattr(other, 'private_key') and self.private_key == other.private_key,
            hasattr(other, 'created') and self.created == other.created,
        ])

    def as_json(self):
        # deliberatey not returning image or cover image
        # because those should be signed urls
        return {
            'display_name': self.display_name,
            'handle': self.handle,
            'user_id': self.user_id,
            'public_key': str(self.public_key),
            'created': str(self.created),
        }
