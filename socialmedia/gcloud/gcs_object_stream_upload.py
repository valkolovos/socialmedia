## flat-out stolen from https://dev.to/sethmichaellarson/python-data-streaming-to-google-cloud-storage-with-resumable-uploads-458h
from google.auth.transport.requests import AuthorizedSession
from google.resumable_media import requests, common
from google.cloud import storage

from werkzeug.utils import secure_filename

def gcs_stream_factory(
    total_content_length, filename, content_type, content_length=None
):
    storage_client = storage.Client()
    filename = secure_filename(filename)
    upload_stream = GCSObjectStreamUpload(
        client=storage_client,
        bucket_name='{}.appspot.com'.format(storage_client.project),
        blob_name=filename,
        content_type=content_type,
    )
    #print("start receiving file ... filename {} => google storage".format(filename))
    upload_stream.start()
    return upload_stream

class GCSObjectStreamUpload():
    def __init__(
            self,
            client: storage.Client,
            bucket_name: str,
            blob_name: str,
            content_type: 'application/octet-stream',
            chunk_size: int=1024 * 1024 # setting this to almost certainly be larger than the incoming buffer size
        ):
        self._client = client
        self._bucket = self._client.bucket(bucket_name)
        self._blob = self._bucket.blob(blob_name)
        self._content_type = content_type

        self._buffer = b''
        self._buffer_size = 0
        self._chunk_size = chunk_size
        self._read = 0
        self.filename = blob_name

        self._transport = AuthorizedSession(
            credentials=self._client._credentials
        )
        self._request = None  # type: requests.ResumableUpload

    def seek(self, pos):
        # Flask appears to use this as an "I'm done" marker
        if pos == 0:
            self.stop()

    def start(self):
        url = (
            f'https://www.googleapis.com/upload/storage/v1/b/'
            f'{self._bucket.name}/o?uploadType=resumable'
        )
        self._request = requests.ResumableUpload(
            upload_url=url, chunk_size=self._chunk_size
        )
        self._request.initiate(
            transport=self._transport,
            content_type=self._content_type,
            stream=self,
            stream_final=False,
            metadata={'name': self._blob.name},
        )

    def stop(self):
        self._request.transmit_next_chunk(self._transport)

    def write(self, data: bytes) -> int:
        data_len = len(data)
        self._buffer_size += data_len
        self._buffer += data
        del data
        while self._buffer_size >= self._chunk_size:
            try:
                self._request.transmit_next_chunk(self._transport)
            except common.InvalidResponse:
                self._request.recover(self._transport)
        return data_len

    def read(self, chunk_size: int) -> bytes:
        # I'm not good with efficient no-copy buffering so if this is
        # wrong or there's a better way to do this let me know! :-)
        to_read = min(chunk_size, self._buffer_size)
        memview = memoryview(self._buffer)
        self._buffer = memview[to_read:].tobytes()
        self._read += to_read
        self._buffer_size -= to_read
        return memview[:to_read].tobytes()

    def tell(self) -> int:
        return self._read
