from rabbitmq_sync.events import BaseEvent

EVENT_TYPE_HTTP_REQUEST = 'http_request'
EVENT_TYPE_HTTP_RESPONSE = 'http_response'


class HttpRequest(BaseEvent):
    method: str
    correlation_id: str
    url: str
    headers: dict
    body: str


class HttpResponse(HttpRequest):
    status_code: int