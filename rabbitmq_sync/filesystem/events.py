from typing import TypedDict, Optional, Union
from typing_extensions import NotRequired

from rabbitmq_sync.events import BaseEvent

# TYPES

from watchdog.events import (
    EVENT_TYPE_DELETED,
    EVENT_TYPE_MODIFIED,
    EVENT_TYPE_CREATED,
    EVENT_TYPE_MOVED,
    EVENT_TYPE_CLOSED
)

EVENT_TYPE_CONTENT = 'content'
EVENT_TYPE_CONTENT_REQUEST = 'content_request'


# EVENTS


class BaseFileEvent(BaseEvent):
    src_path: str
    timestamp: float
    edited_on: NotRequired[float]


class FileSystemEvent(BaseFileEvent):
    is_directory: bool
    dest_path: NotRequired[str]


class FileContent(BaseFileEvent):
    content: bytes | str


class FileContentRequest(BaseFileEvent):
    pass


class TreeRequest(BaseEvent):
    include_content: bool


class Tree(BaseEvent):
    content: dict[str, Union[FileContent]]
