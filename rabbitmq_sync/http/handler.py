import base64
import logging
import sys
from urllib.parse import urlparse
import uuid
import time
import requests
from threading import Thread, Lock

import waitress
from flask import Flask, request, Response
from kombu import Connection, Producer
from kombu.pools import producers
from rabbitmq_sync import definitions
from rabbitmq_sync.events import EVENT_INTERNAL_READY
from .config import ONLY_WITH_PREFIX, PREFIX_TO_DESTINATION, HTTP_TIMEOUT_SECONDS
from .events import *


def register(connection: Connection):
    handler = Handler(connection)

    return {
        EVENT_INTERNAL_READY: handler.on_ready,
        EVENT_TYPE_HTTP_REQUEST: handler.on_rabbit_request,
        EVENT_TYPE_HTTP_RESPONSE: handler.on_rabbit_response
    }


class Handler:

    def __init__(self, connection: Connection):
        self.connection = connection
        self.flask_app = self.create_app()
        self.correlation_id_to_response: dict[str, HttpResponse] = dict()
        self.lock = Lock()

    def create_app(self):
        app = Flask(__name__)

        @app.before_request
        def before_request():
            return self.on_flask_request()

        return app

    def on_ready(self, event):
        if 'no_flask' in sys.argv:
            return logging.info('Not starting flask')

        logging.info('Starting flask app')
        t = Thread(
            target=self.flask_app.run,
            # args=(self.flask_app,),
            kwargs={'port': 8080},
            daemon=True)
        t.start()

    def on_rabbit_request(self, event: HttpRequest):

        func = {
            'GET': requests.get,
            'POST': requests.post,
            'DELETE': requests.delete,
            'PUT': requests.put,
            'PATCH': requests.patch,
        }.get(event['method'], requests.get)

        body = base64.b64decode(event['body'])

        try:
            result = func(
                url=event['url'],
                headers=event['headers'],
                data=body)

            rabbit_response: HttpResponse = {
                'event_type': EVENT_TYPE_HTTP_RESPONSE,
                'correlation_id': event['correlation_id'],
                'method': event['method'],
                'url': event['url'],
                'headers': dict(result.headers),
                'status_code': result.status_code,
                'body': base64.b64encode(result.content).decode('utf-8')
            }

        except requests.exceptions.ConnectionError or requests.exceptions.ConnectTimeout:
            rabbit_response: HttpResponse = {
                'event_type': EVENT_TYPE_HTTP_RESPONSE,
                'correlation_id': event['correlation_id'],
                'method': event['method'],
                'url': event['url'],
                'headers': dict(),
                'status_code': -1,
                'body': ''
            }

        self.publish(rabbit_response)

    def on_rabbit_response(self, event: HttpResponse):
        with self.lock:
            self.correlation_id_to_response[event['correlation_id']] = event

    def on_flask_request(self):
        rabbit_request = self.get_rabbit_request()
        self.publish(rabbit_request)

        return self.wait_response(rabbit_request['correlation_id'])

    def get_rabbit_request(self):
        correlation_id = str(uuid.uuid4())
        url = self.get_proxy_url(request.url)
        body = base64.b64encode(request.data).decode('utf-8')

        rabbit_request: HttpRequest = {
            'event_type': EVENT_TYPE_HTTP_REQUEST,
            'correlation_id': correlation_id,

            'method': request.method,
            'url': url,
            'headers': dict(request.headers),
            'body': body
        }

        return rabbit_request

    def get_proxy_url(self, url: str):
        parsed = urlparse(url)

        location = parsed.path
        slash, prefix, other = location.split('/', 2)
        prefix: str

        if prefix in PREFIX_TO_DESTINATION:
            parsed = parsed\
                ._replace(netloc=PREFIX_TO_DESTINATION[prefix])\
                ._replace(path=other)
            return parsed.geturl()
        elif ONLY_WITH_PREFIX:
            raise Exception('Urls only with prefix are allowed')
        else:
            parsed = parsed\
                ._replace(netloc=prefix.removeprefix('/'))\
                ._replace(path=other)
            return parsed.geturl()

    def get_response(self, rabbit_response: HttpResponse):
        response = Response()
        response.headers = rabbit_response['headers']
        response.data = base64.b64decode(rabbit_response['body'])
        response.status_code = rabbit_response['status_code']
        return response

    def wait_response(self, correlation_id: str):
        start_time = time.time()
        while time.time() - start_time < HTTP_TIMEOUT_SECONDS:

            with self.lock:
                maybe_rabbit_response = self.correlation_id_to_response.get(correlation_id)

            if maybe_rabbit_response is not None:
                return self.get_response(maybe_rabbit_response)

            time.sleep(0.1)

        # timeout
        return Response(status=500, headers={'rabbit_timeout': HTTP_TIMEOUT_SECONDS})

    def publish(self, content: dict):
        with producers[self.connection].acquire(block=False) as producer:
            producer: Producer
            producer.publish(content,
                             exchange=definitions.main_exchange,
                             routing_key='event.copy',
                             headers={'client_id': definitions.client_id})