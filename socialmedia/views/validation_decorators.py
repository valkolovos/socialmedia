import functools
import json

from flask import request

from socialmedia.dataclient import datastore_client
from socialmedia.views.utils import decrypt_payload, verify_signature

def json_request(func=None):
    '''
    Extracts data from request and adds it as 'request_data' to kwargs
    '''
    if func is None:
        return functools.partial(json_request)
    @functools.wraps(func)
    def extract_json(*args, **kwargs):
        kwargs['request_data'] = request.get_json()
        return func(*args, **kwargs)
    return extract_json

def validate_request(
    func=None, fields=(
        'enc_payload', 'enc_key', 'signature', 'handle',
        'nonce', 'tag'
    )
):
    '''
    Validates fields exist in request data.
    '''
    if func is None:
        return functools.partial(validate_request, fields=fields)
    @functools.wraps(func)
    def _validate_request(*args, **kwargs):
        if not all(field in kwargs.get('request_data') for field in fields):
            return 'Invalid request - missing required fields', 400
        return func(*args, **kwargs)
    return _validate_request

def validate_handle(func=None):
    '''
    Verifies requestee handle in request_data exists and adds
    the requestee as 'connectee' kwargs
    '''
    if func is None:
        return functools.partial(validate_handle)
    @functools.wraps(func)
    def _validate_handle(*args, **kwargs):
        # verify handle exists
        query = datastore_client.query(kind='Profile')
        query.add_filter('handle', '=', kwargs['request_data']['handle'])
        query_results = list(query.fetch(limit=1))
        if not query_results:
            return 'No such handle', 404
        kwargs['connectee'] = query_results[0]
        return func(*args, **kwargs)
    return _validate_handle

def validate_payload(func=None, fields=()):
    '''
    Decrypts the encrypted payload and adds it to kwargs as 'request_payload'.
    Also verifies fields exist in the decrypted payload.
    '''
    if func is None:
        return functools.partial(validate_payload)
    @functools.wraps(func)
    def _validate_payload(*args, **kwargs):
        # decrypt and verify payload
        try:
            request_payload = decrypt_payload(
                kwargs['connectee'],
                kwargs['request_data']['enc_key'],
                kwargs['request_data']['enc_payload'],
                kwargs['request_data']['nonce'],
                kwargs['request_data']['tag'],
            )
        except json.JSONDecodeError:
            return 'Invalid payload - unable to convert to JSON', 400
        # verify request payload
        if not all(field in request_payload for field in fields):
            return 'Invalid request - missing required fields', 400
        kwargs['request_payload'] = request_payload
        return func(*args, **kwargs)
    return _validate_payload

def validate_connection(func=None, host_key='host', handle_key='handle'):
    '''
    Validates requestor and requestee have a valid connection. Adds
    requestor to kwargs as 'requestor'. Verifies signature of request
    against locally stored public key
    '''
    if func is None:
        return functools.partial(
            validate_connection, host_key=host_key, handle_key=handle_key
        )
    @functools.wraps(func)
    def _validate_connection(*args, **kwargs):
        # check connection status
        query = datastore_client.query(kind='Connection')
        query.ancestor = kwargs['connectee'].key
        query.add_filter('status', '=', 'connected')
        query.add_filter('handle', '=', kwargs['request_payload'][handle_key])
        query.add_filter('host', '=', kwargs['request_payload'][host_key])
        query_results = list(query.fetch(limit=1))
        if not query_results:
            return 'No connection found', 404
        requestor = kwargs['requestor'] = query_results[0]
        # verify signature
        if not verify_signature(
            requestor, kwargs['request_data']['signature'],
            kwargs['request_payload']
        ):
            return 'Invalid request - signature does not match', 400
        return func(*args, **kwargs)
    return _validate_connection

