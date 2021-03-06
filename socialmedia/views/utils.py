import base64
import json

from datetime import datetime
from dateutil import tz

from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
# using this instead of json.dumps because it handles datetimes
from flask.json import dumps
from google.cloud import datastore

from socialmedia.dataclient import datastore_client

def enc_and_sign_payload(user, connection, payload, json_default=None):
    key = Random.get_random_bytes(16)
    user_key = RSA.importKey(user['private_key'])
    # connection's key
    conn_key = RSA.importKey(connection['public_key'])
    # convert json payload to bytes
    payload_as_bytes = dumps(payload, default=json_default).encode()
    # get encoding key from connection key
    cipher_rsa = PKCS1_OAEP.new(conn_key)
    enc_key = cipher_rsa.encrypt(key)
    cipher_aes = AES.new(key, AES.MODE_EAX)
    enc_payload, tag = cipher_aes.encrypt_and_digest(payload_as_bytes)
    signature_hash = SHA256.new(payload_as_bytes)
    signature = pkcs1_15.new(user_key).sign(signature_hash)
    return (
        base64.b64encode(enc_payload).decode(),
        base64.b64encode(enc_key).decode(),
        signature.hex(),
        cipher_aes.nonce.hex(),
        tag.hex(),
    )

def decrypt_payload(user, enc_key, enc_payload, nonce, tag):
    user_key = RSA.importKey(user['private_key'])
    cipher_rsa = PKCS1_OAEP.new(user_key)
    encrypt_key = cipher_rsa.decrypt(base64.b64decode(enc_key))
    cipher_aes = AES.new(encrypt_key, AES.MODE_EAX, bytes.fromhex(nonce))
    decrypt_payload = cipher_aes.decrypt_and_verify(
        base64.b64decode(enc_payload), bytes.fromhex(tag)
    )
    return json.loads(decrypt_payload)

def verify_signature(connection, signature, payload):
    connect_key = RSA.importKey(connection['public_key'])
    payload_as_bytes = dumps(payload).encode()
    signature_hash = SHA256.new(payload_as_bytes)
    pkcs1_15.new(connect_key).verify(signature_hash, bytes.fromhex(signature))
    return True

def create_profile(user_id, display_name, handle):
    random_generator = Random.new().read
    crypto_key = RSA.generate(2048, random_generator)
    key = datastore_client.key('Profile')
    profile = datastore.Entity(key=key, exclude_from_indexes=('public_key', 'private_key'))
    profile.update({
        'display_name': display_name,
        'handle': handle,
        'created': datetime.now().astimezone(tz.UTC),
        'user_id': user_id,
        'public_key': crypto_key.publickey().exportKey(),
        'private_key': crypto_key.exportKey(),
    })
    datastore_client.put(profile)
    return profile
