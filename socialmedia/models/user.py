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
        self.password = None

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

    def __str__(self):
        return f'id: {self.id}, email: {self.email}, admin: {self.admin}'

    def __repr__(self):
        return f'User(id: {self.id}, email: {self.email}, admin: {self.admin}, ' \
            f'has_password: {hasattr(self, "password") and self.password is not None})'

    def __eq__(self, other):
        return all([
            type(other) == type(self),
            hasattr(other, 'id') and self.id == other.id,
            hasattr(other, 'email') and self.email == other.email,
            hasattr(other, 'admin') and self.admin == other.admin,
            hasattr(other, 'password') and self.password == other.password,
        ])

    def as_json(self):
        return {
            'id': self.id,
            'email': self.email,
            'admin': self.admin,
        }

