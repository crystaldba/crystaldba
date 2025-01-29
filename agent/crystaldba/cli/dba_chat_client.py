import logging
from typing import Iterator

import requests

from crystaldba.cli.chat_requester import ChatRequester
from crystaldba.shared.api import ChatRequest
from crystaldba.shared.api import ChatResponse
from crystaldba.shared.api import DbaChatSyncProtocol
from crystaldba.shared.constants import API_ENDPOINTS
from crystaldba.shared.constants import CRYSTAL_API_URL


class DbaChatClient(DbaChatSyncProtocol):
    def __init__(
        self,
        chat_requester: ChatRequester,
    ):
        self.chat_requester = chat_requester
        self.logger = logging.getLogger(__name__)

        try:
            self.thread_id = self.chat_requester.request(f"{CRYSTAL_API_URL}{API_ENDPOINTS['CHAT_START']}")["thread_id"]
            self.logger.info(f"Created chat thread: {self.thread_id}")
        except requests.HTTPError as e:
            self.logger.critical(f"Error creating chat thread: {e!r}")
            raise ValueError(f"Error creating chat thread: {e!s}") from e

    def turn(self, request: ChatRequest) -> Iterator[ChatResponse]:
        self.logger.debug("Client_response_followup: turn : begin")
        try:
            self.logger.debug(f"CLIENT_LOOP: Sending request {request} to server")
            for response in self.chat_requester.request_stream(
                f"{CRYSTAL_API_URL}{API_ENDPOINTS['CHAT_CONTINUE'].format(thread_id=self.thread_id)}",
                request,
            ):
                if response is not None and response != "":
                    chat_response = ChatResponse.model_validate_json(json_data=response)
                    self.logger.debug(f"Received response from server: {chat_response}")
                    yield chat_response
                else:
                    self.logger.debug("Received empty response from server")
                    yield from ()
        except requests.HTTPError:
            # print(f"Error sending message: {e!s}")
            raise
