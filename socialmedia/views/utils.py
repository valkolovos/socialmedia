import asyncio
import base64
import dateparser
import json
import requests

from collections import defaultdict

from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from flask import current_app, url_for
# using this instead of json.dumps because it handles datetimes
from flask.json import dumps

from socialmedia import models

def enc_and_sign_payload(profile, connection, payload, json_default=None):
    # profile is requesting profile and must have a private key
    # connection is requested connection which will only have public key
    key = Random.get_random_bytes(16)
    user_key = RSA.importKey(profile.private_key)
    # connection's key
    conn_key = RSA.importKey(connection.public_key)
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
    user_key = RSA.importKey(user.private_key)
    cipher_rsa = PKCS1_OAEP.new(user_key)
    encrypt_key = cipher_rsa.decrypt(base64.b64decode(enc_key))
    cipher_aes = AES.new(encrypt_key, AES.MODE_EAX, bytes.fromhex(nonce))
    decrypt_payload = cipher_aes.decrypt_and_verify(
        base64.b64decode(enc_payload), bytes.fromhex(tag)
    )
    return json.loads(decrypt_payload)

def verify_signature(connection, signature, payload):
    connect_key = RSA.importKey(connection.public_key)
    payload_as_bytes = dumps(payload).encode()
    signature_hash = SHA256.new(payload_as_bytes)
    pkcs1_15.new(connect_key).verify(signature_hash, bytes.fromhex(signature))
    return True

def create_profile(user_id, display_name, handle):
    profile = current_app.datamodels.Profile(
        display_name=display_name,
        handle=handle,
        user_id=user_id,
    )
    profile.save()
    return profile

def get_message_comments(messages, comment_references, request_host):
    commentors = defaultdict(list)
    # cheap hack to create a set of commentors by using the ids as keys
    all_commentors = {}
    # message_dict to be able to look up messages by id later
    message_dict = {}
    connectee = messages[0].profile
    for message in messages:
        message_dict[message.id] = message
        for comment_reference in comment_references[message.id]:
           commentors[comment_reference.connection.id].append(message)
           all_commentors[comment_reference.connection.id] = comment_reference.connection

    async def get_comments(connection, messages):
        request_payload = {
          'host': request_host,
          'handle': connectee.handle,
          'message_ids': list({m.id for m in messages}),
        }
        # enc_and_sign_payload(profile, connection. request_payload)
        # profile is connectee and connection is requestor
        enc_payload, enc_key, signature, nonce, tag = enc_and_sign_payload(
            connectee, connection, request_payload
        )
        protocol = 'https'
        if connection.host == 'localhost:8080': # pragma: no cover
            protocol = 'http'
        request_url = f'{protocol}://{connection.host}{url_for("external_comms.retrieve_comments")}'
        payload = {
            'enc_payload': enc_payload,
            'enc_key': enc_key,
            'signature': signature,
            'nonce': nonce,
            'tag': tag,
            'handle': connection.handle,
        }
        # send request to connection's host
        response = requests.post(
            request_url,
            json=payload,
        )
        if response.status_code == 200:
            response_data = json.loads(response.content)
            response_payload = decrypt_payload(
                connectee,
                response_data['enc_key'],
                response_data['enc_payload'],
                response_data['nonce'],
                response_data['tag'],
            )
            for comment_json in response_payload:
                comment = models.Comment(
                    profile=models.Profile(
                        handle=comment_json['profile']['handle'],
                        display_name=comment_json['profile']['display_name'],
                        public_key=comment_json['profile']['public_key'],
                        user_id=comment_json['profile']['user_id'],
                    ),
                    message_id=comment_json['message_id'],
                    text=comment_json['text'],
                    files=comment_json['files'],
                    created=dateparser.parse(
                        comment_json['created'], settings={'TIMEZONE': 'UTC'}
                    ),
                )
                message_dict[comment.message_id].comments.add(comment)
        else:
            for message in messages:
                message_dict[message.id].comments.add(
                    models.Comment(
                        profile=models.Profile(
                            handle=connection.handle,
                            display_name=connection.display_name,
                        ),
                        text='error retrieving comments',
                        message_id=message.id,
                    )
                )
            print(f'Unable to retrieve comments {response.status_code}')
            print(response.headers)
            print(response.content)

    async def collect_comments():
        gather = asyncio.gather()
        for commentor in all_commentors.values():
            asyncio.gather(get_comments(commentor, commentors[commentor.id]))
        await gather

    asyncio.run(collect_comments())
