import logging
import os
import time
from pathlib import Path
from kombu import Connection, Producer
from kombu.pools import producers
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rabbitmq_sync import definitions
from .events import *


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, connection: Connection):
        self.connection = connection

    def on_any_event(self, event):
        dict_event: FileSystemEvent = self.get_dict(event)
        with producers[self.connection].acquire(block=False) as producer:
            producer: Producer
            producer.publish(dict_event,
                             exchange=definitions.main_exchange,
                             routing_key='event.file',
                             headers={'client_id': definitions.client_id})

    def get_dict(self, event) -> FileSystemEvent:
        now = time.time()

        dict_event: FileSystemEvent = {
            'timestamp': now,
            'edited_on': now,
            'event_type': event.event_type,
            'is_directory': event.is_directory,
            'src_path': str(os.path.relpath(event.src_path))
        }

        if hasattr(event, 'dest_path'):
            dict_event['dest_path'] = str(os.path.relpath(event.dest_path))

        return dict_event


def start_observing_filesystem(path: Path, connection: Connection):
    abspath = os.path.abspath(path)
    logging.info('Observing filesystem at %s', abspath)

    handler = FileChangeHandler(connection)
    observer = Observer()
    observer.schedule(handler, abspath, recursive=True)
    observer.start()
    observer.join(0)
    return observer
