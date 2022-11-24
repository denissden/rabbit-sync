from rabbitmq_sync.events import BaseEvent

EVENT_TYPE_CONTENT = 'content'
EVENT_TYPE_REQUEST_ALL = 'request_all'


class FilePath(BaseEvent):
    path: str


class FileContent(FilePath):
    content: str
