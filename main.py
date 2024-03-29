import os

from socialmedia import create_app, datastore as gcloud_datastore
from socialmedia.gcloud.gcs_object_stream_upload import gcs_stream_factory
from socialmedia.gcloud.utils import (
    generate_signed_urls,
    get_shas,
    TaskManager,
    update_backend,
    update_frontend,
)

from google.cloud import datastore

try:
    import googleclouddebugger
    googleclouddebugger.enable(
        breakpoint_enable_canary=True
    )
except ImportError:
    pass

app = create_app(
    gcloud_datastore,
    gcs_stream_factory,
    generate_signed_urls,
    TaskManager(
        datastore.Client().project, 'us-west2',
        os.environ.get('ASYNC_TASKS', 'true').lower() == 'true'
    ),
    get_shas,
    update_backend,
    update_frontend,
)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
