import json
import sys
from typing import Callable
from typing import Iterator
from typing import Optional

if sys.version_info >= (3, 12):
    from typing import override
else:
    # Define a no-op decorator
    def override(method: Callable) -> Callable:
        return method


import requests
from rich.console import Console
from sseclient import SSEClient

from crystaldba.shared.api import ChatRequest
from crystaldba.shared.secure_session import SecureSession


class PostOverrideSession(requests.Session):
    # This is a bit of a dirty hack
    # It might be better to clone the session object and override the get method
    # Here we are deriving from the requests.Session class but most of the implementation
    # is simply missing
    def __init__(self, http_session: SecureSession, data):
        # TODO - call super().__init__()?
        self.http_session = http_session
        self.data = data

    @override
    def get(self, url, **kwargs):
        return self.http_session.post(url, data=self.data, **kwargs)


class ChatRequester:
    def __init__(self, http_session: SecureSession, console: Console):
        self.console = console
        self.http_session = http_session

    def request(self, path: str, request_payload: Optional[ChatRequest] = None):
        # TODO - can se just do http_session.post()?
        prepared_request = self.http_session.prepare_request(
            requests.Request(
                method="POST",
                url=path,
                data=json.dumps(request_payload.model_dump()) if request_payload is not None else None,
            )
        )
        response = self.http_session.send(prepared_request)
        response.raise_for_status()
        return response.json()

    def request_stream(self, path: str, request_payload: Optional[ChatRequest] = None) -> Iterator[str]:
        session = PostOverrideSession(self.http_session, data=json.dumps(request_payload.model_dump()) if request_payload is not None else None)
        for event in SSEClient(path, session=session):
            yield event.data
