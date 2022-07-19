import pytest

from flask import _request_ctx_stack

from unittest.mock import Mock

from socialmedia import create_app

from test import datamodels
from test.datamodels.base import BaseTestModel

def generate_signed_urls(files, expiration=60):
    return [f'test_{f}' for f in files]

@pytest.fixture
def client():
    app = create_app(datamodels, None, generate_signed_urls, Mock(), Mock(), Mock(), Mock())
    with app.test_client() as client:
        # init the flask app context
        client.get('/')
        yield client
    # clean up test data
    BaseTestModel._data = []
