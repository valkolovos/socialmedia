from Crypto import Random
from Crypto.PublicKey import RSA
from datetime import datetime
from dateutil import tz

class Profile():
    def __init__(self, **kwargs):
        now = datetime.now().astimezone(tz.UTC)
        self.display_name = kwargs.get('display_name')
        self.handle = kwargs.get('handle')
        self.user_id = kwargs.get('user_id')
        self.public_key = kwargs.get('public_key')
        self.private_key = kwargs.get('private_key')
        self.created = kwargs.get('created', now)
        if not(any((self.public_key, self.private_key))):
            self.public_key, self.private_key = self.generate_keys()

    def generate_keys(self):
        random_generator = Random.new().read
        crypto_key = RSA.generate(2048, random_generator)
        return crypto_key.publickey().exportKey(), crypto_key.exportKey()

    def as_json(self):
        return {
            'display_name': self.display_name,
            'handle': self.handle,
            'user_id': self.user_id,
            'public_key': str(self.public_key),
            'created': str(self.created),
        }

    def __str__(self):
        return f'display_name: {self.display_name}, handle: {self.handle}, user_id: {self.user_id}'

    def __repr__(self):
        return f'display_name: {self.display_name}, handle: {self.handle}, user_id: {self.user_id}'

    def __eq__(self, other):
        return all([
            hasattr(other, 'display_name') and self.display_name == other.display_name,
            hasattr(other, 'handle') and self.handle == other.handle,
            hasattr(other, 'user_id') and self.user_id == other.user_id,
            hasattr(other, 'public_key') and self.public_key == other.public_key,
            hasattr(other, 'created') and self.created == other.created,
        ])
