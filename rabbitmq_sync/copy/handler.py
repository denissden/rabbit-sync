import base64
import logging
import sys
from kombu import Connection, Producer
from kombu.pools import producers
from .events import *
from .utils import path_edited_on, str_to_path, complain_if_not_in_cwd, cwd
from rabbitmq_sync import definitions
from rabbitmq_sync.events import EVENT_INTERNAL_READY


def register(connection: Connection):
    handler = Handler(connection)

    return {
        EVENT_INTERNAL_READY: handler.on_ready,
        EVENT_TYPE_REQUEST_ALL: handler.on_request,
        EVENT_TYPE_CONTENT: handler.on_content,
    }


class Handler:
    def __init__(self, connection: Connection):
        self.connection = connection

    def on_ready(self, event):
        if 'copy' in sys.argv:
            logging.info('Requesting all content')

            request_all: BaseEvent = {
                'event_type': EVENT_TYPE_REQUEST_ALL,
            }

            self.publish(request_all)

    def on_request(self, event: BaseEvent):
        for p in cwd.rglob('*'):
            if p.is_dir():
                continue

            print(p)

            content: FileContent = {
                'event_type': EVENT_TYPE_CONTENT,
                'path': str(p.relative_to(cwd)),
                'content': base64.b64encode(p.read_bytes()).decode('utf-8')
            }

            self.publish(content)

    def publish(self, content: dict):
        with producers[self.connection].acquire(block=False) as producer:
            producer: Producer
            producer.publish(content,
                             exchange=definitions.main_exchange,
                             routing_key='event.copy',
                             headers={'client_id': definitions.client_id})

    def on_content(self, event: FileContent):
        event_path = str_to_path(event['path'])

        complain_if_not_in_cwd(event_path)

        event_path.parent.mkdir(parents=True, exist_ok=True)

        content_bytes = base64.b64decode(event['content'])

        event_path.write_bytes(content_bytes)
