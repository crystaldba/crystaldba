import pytest
import sqlalchemy
from prompt_toolkit import PromptSession
from pytest_mock import MockerFixture
from rich.console import Console

from crystaldba.cli.chat_requester import ChatRequester
from crystaldba.cli.chat_response_followup import ChatResponseFollowup
from crystaldba.cli.sql_tool import LocalSqlDriver
from crystaldba.shared.api import ChatMessage
from crystaldba.shared.api import ChatRequest
from crystaldba.shared.api import ChatResponse
from crystaldba.shared.api import SQLToolErrorResponse
from crystaldba.shared.api import SQLToolExecuteRequest
from crystaldba.shared.api import SQLToolExecuteResponse
from crystaldba.shared.api import SQLToolSchemaRequest
from crystaldba.shared.api import SQLToolSchemaResponse
from crystaldba.shared.base_sql_driver import BaseSqlDriver


@pytest.fixture
def mock_user_input(mocker: MockerFixture):
    return mocker.Mock(spec=PromptSession)


@pytest.fixture
def mock_console(mocker: MockerFixture):
    return mocker.Mock(spec=Console)


@pytest.fixture
def mock_chat_requester(mocker: MockerFixture):
    return mocker.Mock(spec=ChatRequester)


@pytest.fixture
def mock_sql_driver(mocker: MockerFixture):
    return mocker.Mock(spec=LocalSqlDriver)


@pytest.fixture
def chat_response_followup(mock_console, mock_sql_driver):
    return ChatResponseFollowup(
        mock_console,
        mock_sql_driver,
    )


class TestChatResponseFollowup:
    def test_initialization(self, mock_console, mock_sql_driver):
        """Test successful initialization of ChatResponseFollowup"""
        response_followup = ChatResponseFollowup(mock_console, mock_sql_driver)
        assert response_followup.message_counter == 0

    def test_create_chatrequest(self, chat_response_followup):
        """Test creating a chat request"""
        request = chat_response_followup.create_chatrequest("test message")
        assert isinstance(request, ChatRequest)
        assert request.sequence_id == 0
        assert request.continuation_token is None
        assert isinstance(request.payload, ChatMessage)
        assert request.payload.message == "test message"

    def test_from_chatresponse_to_possible_new_chatrequest_sql_execute(self, chat_response_followup):
        """Test handling SQLToolExecuteRequest response"""
        response = ChatResponse(sequence_id=1, continuation_token="token", payload=SQLToolExecuteRequest(query="SELECT 1"))
        row = BaseSqlDriver.RowResult(cells={"result": 1})
        chat_response_followup.sql_driver.execute_query.return_value = [row]

        result = chat_response_followup.from_chatresponse_to_possible_new_chatrequest(response)

        assert isinstance(result, ChatRequest)
        assert isinstance(result.payload, SQLToolExecuteResponse)
        assert result.sequence_id == response.sequence_id
        assert result.continuation_token == response.continuation_token
        assert result.payload.rows == [{"result": 1}]

    def test_from_chatresponse_to_possible_new_chatrequest_schema(self, chat_response_followup):
        """Test handling SQLToolSchemaRequest response"""
        schema_response = ChatResponse(
            sequence_id=1, continuation_token="token", payload=SQLToolSchemaRequest(table_name="test_table", db_schema="public")
        )
        chat_response_followup.sql_driver.get_table_schema.return_value = "test schema"

        result = chat_response_followup.from_chatresponse_to_possible_new_chatrequest(schema_response)

        assert isinstance(result, ChatRequest)
        assert isinstance(result.payload, SQLToolSchemaResponse)
        assert result.sequence_id == 1
        assert result.continuation_token == "token"

    def test_turn_complex_sql_types(self, chat_response_followup):
        """Test handling of complex SQL data types"""
        from datetime import date
        from datetime import datetime
        from datetime import time
        from decimal import Decimal
        from uuid import UUID

        complex_data = {
            "datetime": datetime.now(),
            "date": date.today(),
            "time": time(12, 34, 56),
            "decimal": Decimal("123.45"),
            "uuid": UUID("12345678-1234-5678-1234-567812345678"),
            "bytes": b"binary data",
            "array": [1, 2, 3],
        }
        row = BaseSqlDriver.RowResult(cells=complex_data)
        chat_response_followup.sql_driver.execute_query.return_value = [row]

        response = ChatResponse(sequence_id=1, continuation_token="token", payload=SQLToolExecuteRequest(query="SELECT complex_types"))

        result = chat_response_followup.from_chatresponse_to_possible_new_chatrequest(response)

        assert isinstance(result, ChatRequest)
        assert isinstance(result.payload, SQLToolExecuteResponse)
        assert result.payload.rows
        assert len(result.payload.rows) > 0
        for value in result.payload.rows[0].values():
            assert isinstance(value, (str, int, float, bool, list, type(None)))

    def test_sqltoolerrorresponse_passes_errors_back_to_the_llm(self, chat_response_followup):
        """Test SQL incorrect query get sent back to the LLM"""
        operational_error = sqlalchemy.exc.OperationalError("statement", {}, "connection error")
        chat_response_followup.sql_driver.execute_query.return_value = []  # Default return value
        chat_response_followup.sql_driver.execute_query.side_effect = operational_error

        response = ChatResponse(sequence_id=1, continuation_token="token", payload=SQLToolExecuteRequest(query="SELECT 1"))

        result = chat_response_followup.from_chatresponse_to_possible_new_chatrequest(response)

        assert isinstance(result, ChatRequest)
        assert isinstance(result.payload, SQLToolErrorResponse)
        assert "OperationalError" in result.payload.error_string

    def test_sqltoolerrorresponse_passes_errors_back_to_the_llm_programming_error(self, chat_response_followup):
        """Test handling of SQL programming errors"""
        programming_error = sqlalchemy.exc.ProgrammingError("statement", {}, "syntax error")
        chat_response_followup.sql_driver.execute_query.side_effect = programming_error

        response = ChatResponse(sequence_id=1, continuation_token="token", payload=SQLToolExecuteRequest(query="SELECT invalid_syntax"))

        result = chat_response_followup.from_chatresponse_to_possible_new_chatrequest(response)

        assert isinstance(result, ChatRequest)
        assert isinstance(result.payload, SQLToolErrorResponse)
        assert "ProgrammingError" in result.payload.error_string

    def test_sqltoolerrorresponse_passes_errors_back_to_the_llm_sql_error(self, chat_response_followup):
        """Test handling SQL execution errors"""
        generic_error = Exception("Generic SQL Error")
        chat_response_followup.sql_driver.execute_query.side_effect = generic_error

        response = ChatResponse(sequence_id=1, continuation_token="token", payload=SQLToolExecuteRequest(query="SELECT 1"))

        result = chat_response_followup.from_chatresponse_to_possible_new_chatrequest(response)

        assert isinstance(result, ChatRequest)
        assert isinstance(result.payload, SQLToolErrorResponse)
        assert "Exception: Generic SQL Error" in result.payload.error_string

    def test_get_schema_with_invalid_table(self, chat_response_followup):
        """Test schema request for non-existent table"""
        chat_response_followup.sql_driver.get_table_schema.return_value = None

        response = ChatResponse(
            sequence_id=1, continuation_token="token", payload=SQLToolSchemaRequest(table_name="nonexistent_table", db_schema="public")
        )

        result = chat_response_followup.from_chatresponse_to_possible_new_chatrequest(response)

        assert isinstance(result, ChatRequest)
        assert isinstance(result.payload, SQLToolSchemaResponse)
        assert result.payload.table_schema is None
