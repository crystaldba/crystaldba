import logging
import time
from typing import Protocol

import sqlalchemy.exc
from rich.console import Console

from crystaldba.cli.sql_tool import LocalSqlDriver
from crystaldba.shared.api import ChatMessage
from crystaldba.shared.api import ChatMessageDone
from crystaldba.shared.api import ChatMessageFragment
from crystaldba.shared.api import ChatRequest
from crystaldba.shared.api import ChatResponse
from crystaldba.shared.api import SQLToolErrorResponse
from crystaldba.shared.api import SQLToolExecuteRequest
from crystaldba.shared.api import SQLToolSchemaRequest
from crystaldba.shared.api import SQLToolSchemaResponse
from crystaldba.shared.base_sql_driver import BaseSqlDriver
from crystaldba.shared.sql_serialization import to_sql_tool_response


class ChatResponseFollowupProtocol(Protocol):
    """Protocol defining the interface for chat stepping functionality."""

    def create_chatrequest(self, message: str) -> ChatRequest:
        """Create a new chat request from a message."""
        ...

    def from_chatresponse_to_possible_new_chatrequest(self, chat_response: ChatResponse) -> str | ChatRequest | None:
        """Send a chat request and handle the response."""
        ...


class ChatResponseFollowup(ChatResponseFollowupProtocol):
    def __init__(
        self,
        console: Console,
        sql_driver: LocalSqlDriver,
    ):
        self.sql_driver = sql_driver
        self.logger = logging.getLogger(__name__)
        self.console = console
        self.message_counter = 0

    def create_chatrequest(self, message: str) -> ChatRequest:
        return ChatRequest(
            sequence_id=self.message_counter,
            continuation_token=None,
            payload=ChatMessage(message=message),
        )

    def from_chatresponse_to_possible_new_chatrequest(self, chat_response: ChatResponse) -> str | ChatRequest | None:
        self.logger.debug("chat_response_followup: from_chatresponse_to_possible_new_chatrequest: begin")
        match chat_response.payload:
            case ChatMessage():
                self.message_counter += 1
                return chat_response.payload.message
            case ChatMessageFragment():
                return chat_response.payload.message_fragment
            case ChatMessageDone():
                self.message_counter += 1
                return None
            case SQLToolExecuteRequest():
                self.logger.debug(f"CLIENT_LOOP: Executing query: {chat_response.payload.query}")
                try:
                    print(f"Executing query: {chat_response.payload.query}\n")
                    result = self._execute_sql_query_with_retry(chat_response.payload.query)
                    json_serializable_result = to_sql_tool_response(result)
                    self.logger.debug(f"CLIENT_LOOP: Executed successfully. Returning SQLToolExecuteResponse: {json_serializable_result}")
                    return ChatRequest(
                        sequence_id=chat_response.sequence_id,
                        continuation_token=chat_response.continuation_token,
                        payload=json_serializable_result,
                    )
                except Exception as e:
                    self.logger.debug("CLIENT_LOOP: SQLToolExecuteRequest exception")
                    return ChatRequest(
                        sequence_id=chat_response.sequence_id,
                        continuation_token=chat_response.continuation_token,
                        payload=SQLToolErrorResponse(error_string=f"{type(e).__name__}: {e!s}"),
                    )

            case SQLToolSchemaRequest():
                self.logger.debug(
                    f"CLIENT_LOOP: Getting schema for table {chat_response.payload.table_name} in schema {chat_response.payload.db_schema}"
                )
                try:
                    schema = self.sql_driver.get_table_schema(table_name=chat_response.payload.table_name, schema=chat_response.payload.db_schema)
                    return ChatRequest(
                        sequence_id=chat_response.sequence_id,
                        continuation_token=chat_response.continuation_token,
                        payload=SQLToolSchemaResponse(
                            table_schema=schema,
                        ),
                    )
                except Exception as e:
                    self.logger.debug("CLIENT_LOOP: exception: SQLToolSchemaRequest")
                    return ChatRequest(
                        sequence_id=chat_response.sequence_id,
                        continuation_token=chat_response.continuation_token,
                        payload=SQLToolErrorResponse(error_string=f"{e}"),
                    )
            case _:
                raise ValueError(f"Unknown response type: {type(chat_response.payload)}")

    def _execute_sql_query_with_retry(self, query: str, max_retries: int = 3, base_delay: int = 1) -> list[BaseSqlDriver.RowResult] | None:
        """Execute a SQL query with exponential backoff retry logic.

        Args:
            query: The SQL query to execute
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds between retries

        Returns:
            The query result or None if no results

        Raises:
            Exception: If all retry attempts fail
        """

        for attempt in range(max_retries):
            try:
                result = self.sql_driver.execute_query(query)
                return result
            except sqlalchemy.exc.OperationalError as e:
                # Only retry on connection-related errors
                if "connection" not in str(e).lower() and "timeout" not in str(e).lower():
                    raise
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    self.logger.warning(f"Connection error on attempt {attempt + 1}: {e!s}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Connection failed after {max_retries} attempts: {e!s}")
                    raise  # Re-raise the last exception if all retries failed
            except Exception as e:
                # Don't retry on other exceptions
                self.logger.info(f"Query failed: {e!s}")
                raise
