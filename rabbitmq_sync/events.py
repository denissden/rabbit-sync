from typing import TypedDict, Optional

EVENT_TYPE_PING = 'ping'
EVENT_TYPE_PONG = 'pong'
EVENT_INTERNAL_READY = 'ready'


class BaseEvent(TypedDict):
    event_type: str


class PingPong(BaseEvent):
    pong: bool
