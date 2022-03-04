from uuid import uuid4
from Crypto.Hash import SHA256

class User:
    '''
    A user maintains basic authentication information - email, password, unique id
    '''

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.email = kwargs.get('email')
        self.admin = kwargs.get('admin', False)

    def set_password(self, password):
        self.password = self.enc_password(password)

    @classmethod
    def enc_password(cls, password):
        h = SHA256.new()
        h.update(bytes(password, 'utf-8'))
        return h.hexdigest()

    @classmethod
    def generate_uuid(cls):
        return str(uuid4())

    def as_json(self):
        return {
            'email': self.email,
            'admin': self.admin,
        }

    def __str__(self):
        return f'id: {self.id}, email: {self.email}, admin: {self.admin}'

    def __repr__(self):
        return f'id: {self.id}, email: {self.email}, admin: {self.admin}'

    def __eq__(self, other):
        return all([
            hasattr(other, 'id') and self.id == other.id,
            hasattr(other, 'email') and self.email == other.email,
        ])
