from kombu import Connection
from rabbitmq_sync.filesystem.utils import cwd
from rabbitmq_sync.filesystem.watcher import start_observing_filesystem
from .definitions import create, delete
from .rabbitmq import Worker, HandlersType
from . import events


def start(rabbit_url: str):
    from kombu import Connection
    from kombu.utils.debug import setup_logging

    # setup root logger
    setup_logging(loglevel='INFO', loggers=[''])

    with Connection(rabbit_url) as conn:
        start_observing_filesystem(cwd, conn)

        channel = conn.channel()
        create(channel)

        handlers = get_handlers(conn)
        try:
            worker = Worker(conn, handlers)
            worker.run()
        except KeyboardInterrupt:
            delete(channel)
            print('bye bye')


def get_handlers(connection: Connection) -> HandlersType:
    from rabbitmq_sync.filesystem import register as register_filesystem

    return [
        register_filesystem(connection)
    ]
