from typing import Callable

from kombu import Connection, Message
from kombu.mixins import ConsumerProducerMixin
from . import definitions
from .definitions import main_queue, main_exchange
from .events import BaseEvent, PingPong, EVENT_TYPE_PING, EVENT_TYPE_PONG

HandlersType = list[dict[str, Callable[[BaseEvent], None]]]


class Worker(ConsumerProducerMixin):
    def __init__(self, connection: Connection, handlers: HandlersType):
        self.connection = connection
        self.handlers = handlers

        self.active_clients = set()

    def on_consume_ready(self, connection, channel, consumers, **kwargs):
        self.ping()

    def ping(self):
        ping: PingPong = {
            'event_type': EVENT_TYPE_PING,
            'pong': False
        }

        self.producer.publish(ping,
                              exchange=main_exchange,
                              routing_key=PingPong.__name__,
                              headers={'client_id': definitions.client_id})

    def get_consumers(self, consumer_class, channel):
        return [consumer_class(main_queue, callbacks=[self.on_message])]

    def on_message(self, body: BaseEvent, message: Message):
        print(body, message)

        if body['event_type'] == EVENT_TYPE_PING:
            self.on_ping()
        elif body['event_type'] == EVENT_TYPE_PONG:
            self.on_pong(message)

        self.process_handlers(body)

        message.ack()

    def process_handlers(self, event: BaseEvent):
        for handler in self.handlers:
            handler_func = handler.get(event['event_type'])
            if handler_func is not None:
                handler_func(event)

    def on_ping(self):
        pong: PingPong = {
            'event_type': EVENT_TYPE_PONG,
            'pong': True
        }
        print('publish')
        self.producer.publish(pong,
                              exchange=main_exchange,
                              routing_key='event',
                              headers={'client_id': definitions.client_id})

    def on_pong(self, message: Message):
        self.active_clients.add(message.headers['client_id'])
