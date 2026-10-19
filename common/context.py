"""Per-request correlation context shared by middleware, services and logging."""

from contextvars import ContextVar, Token
from uuid import uuid4

_request_id: ContextVar[str] = ContextVar("deeplrn_request_id", default="")


def new_request_id() -> str:
    return uuid4().hex


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str) -> Token:
    return _request_id.set(value)


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)
