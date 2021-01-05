import datetime
import json
import os

# pip install requests
import requests

# pip install google-auth
from google.oauth2 import service_account
from google.cloud import storage, tasks_v2

def generate_signed_url(bucket_name, object_name, expiration=60):
    if expiration > 604800:
        raise Exception('Expiration Time can\'t be longer than 604800 seconds (7 days).')

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    creds_file = '/srv/service-account-creds.json'
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    credentials = service_account.Credentials.from_service_account_file(creds_file)
    signed_url = blob.generate_signed_url(
        version='v4',
        expiration=datetime.timedelta(seconds=expiration),
        credentials=credentials,
        method="GET"
    )
    return signed_url

class TaskManager():

    def __init__(self, project, queue_location, use_async=True):
        self.task_client = tasks_v2.CloudTasksClient()
        self.project = project
        self.queue_location = queue_location
        self.use_async = use_async
        print(f'TaskManager use_async={self.use_async}')

    def queue_task(self, payload, queue_name, relative_uri):
        if self.use_async:
            parent = self.task_client.queue_path(self.project, self.queue_location, queue_name)
            task = {
                'app_engine_http_request': {
                    'http_method': 'POST',
                    'relative_uri': relative_uri,
                    'body': json.dumps(payload).encode(),
                    'headers': {
                        'Content-Type': 'application/json',
                    },
                }
            }
            self.task_client.create_task(parent=parent, task=task)
        else:
            requests.post(
                'http://localhost:8080{}'.format(relative_uri),
                json=payload
            )
