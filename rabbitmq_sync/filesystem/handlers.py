import time
from functools import wraps

from kombu import Connection, Producer
from kombu.pools import producers
from .events import *
from .utils import path_edited_on, str_to_path, complain_if_not_in_cwd
from .config import DIFF_POSTFIX
from rabbitmq_sync.utils import git_diff_resolve
from rabbitmq_sync import definitions


def register(connection: Connection):
    handler = FileSystemEventHandler(connection)

    def wrap_check(func):
        @wraps(func)
        def wrapper(event: BaseFileEvent):
            event_path = str_to_path(event['src_path'])
            complain_if_not_in_cwd(event_path)
            func(event)

        return wrapper

    return {
        EVENT_TYPE_MODIFIED: wrap_check(handler.on_modified),
        EVENT_TYPE_CONTENT_REQUEST: wrap_check(handler.on_content_request),
        EVENT_TYPE_CONTENT: wrap_check(handler.on_content),
    }


class FileSystemEventHandler:
    def __init__(self, connection: Connection):
        self.connection = connection

    def on_modified(self, event: FileSystemEvent):
        if event['is_directory']:
            return

        if self.is_event_newer(event):
            request: FileContentRequest = {
                'event_type': EVENT_TYPE_CONTENT_REQUEST,
                'src_path': event['src_path'],
                'timestamp': time.time(),
            }
            self.publish(request)

    def on_content_request(self, event: FileContentRequest):
        event_path = str_to_path(event['src_path'])

        response: FileContent = {
            'event_type': EVENT_TYPE_CONTENT,
            'src_path': str(event_path),
            'content': event_path.read_text(),
            'edited_on': path_edited_on(event_path),
            'timestamp': time.time(),
        }

        self.publish(response)

    def on_content(self, event: FileContent):
        event_path = str_to_path(event['src_path'])
        event_content = event['content']
        try:
            local_content = event_path.read_text()
        except FileNotFoundError:
            local_content = ''

        if local_content == event_content:
            return

        if self.has_diff(local_content) != self.has_diff(event_content):
            return

        take_event_diff = self.is_event_newer(event)

        new_content = git_diff_resolve(
            local_content,
            event_content,
            auto_resolve='b' if take_event_diff else 'a',
            diff_postfix=DIFF_POSTFIX)

        event_path.write_text(new_content)

    @staticmethod
    def has_diff(content: str):
        return DIFF_POSTFIX in content


    @staticmethod
    def is_event_newer(event: BaseFileEvent):
        event_path = str_to_path(event['src_path'])
        event_timestamp = event['timestamp']
        event_edited_on = event.get('edited_on')

        local_edit_time = path_edited_on(event_path)

        if event_edited_on is not None:
            return event_edited_on > local_edit_time
        return event_timestamp > local_edit_time

    def publish(self, content: dict):
        with producers[self.connection].acquire(block=False) as producer:
            producer: Producer
            producer.publish(content,
                             exchange=definitions.main_exchange,
                             routing_key='event.file',
                             headers={'client_id': definitions.client_id})
