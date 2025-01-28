import pytest
import requests
from pytest_mock import MockerFixture
from pytest_mock import MockFixture

from crystaldba.cli.chat_requester import ChatRequester
from crystaldba.cli.dba_chat_client import DbaChatClient
from crystaldba.shared.api import ChatMessage
from crystaldba.shared.api import ChatMessageFragment
from crystaldba.shared.api import ChatRequest
from crystaldba.shared.api import ChatResponse
from crystaldba.shared.constants import API_ENDPOINTS
from crystaldba.shared.constants import CRYSTAL_API_URL


@pytest.fixture
def mock_chat_requester(mocker: MockerFixture):
    requester = mocker.Mock(spec=ChatRequester)
    # Default successful thread creation response
    requester.request.return_value = {"thread_id": "test-thread-123"}
    return requester


@pytest.fixture
def dba_chat_client(mock_chat_requester):
    return DbaChatClient(mock_chat_requester)


class TestDbaChatClient:
    def test_initialization(self, mock_chat_requester):
        """Test successful initialization of DbaChatClient"""
        client = DbaChatClient(mock_chat_requester)
        assert client.thread_id == "test-thread-123"
        mock_chat_requester.request.assert_called_once()

    def test_initialization_failure(self, mock_chat_requester):
        """Test initialization fails appropriately when server returns an error"""
        mock_chat_requester.request.side_effect = requests.HTTPError("Failed to create thread")

        with pytest.raises(ValueError, match="Error creating chat thread"):
            DbaChatClient(mock_chat_requester)

    def test_successful_turn(self, dba_chat_client, mock_chat_requester):
        """Test successful chat turn with valid response"""
        # Reset mock to clear initialization call
        mock_chat_requester.request.reset_mock()

        # Setup mock response for turn
        mock_response = ChatResponse(
            sequence_id=1,
            continuation_token="token123",
            payload=ChatMessageFragment(message_fragment="Test response"),
        ).model_dump_json()
        mock_chat_requester.request_stream.return_value = iter([mock_response])
        mock_chat_requester.request_stream.return_value = iter([mock_response])

        # Create test request
        test_request = ChatRequest(sequence_id=1, continuation_token=None, payload=ChatMessage(message="Test message"))

        # Execute turn
        response_generator = dba_chat_client.turn(test_request)
        responses = list(response_generator)

        # Verify response
        assert all(isinstance(r, ChatResponse) for r in responses)
        assert isinstance(responses[0].payload, ChatMessageFragment)
        assert responses[0].payload.message_fragment == "Test response"
        assert responses[0].sequence_id == 1
        assert responses[0].continuation_token == "token123"
        assert len(responses) == 1
        mock_chat_requester.request_stream.assert_called_once()

    def test_turn_http_error(self, dba_chat_client, mock_chat_requester, mocker: MockFixture):
        """Test chat turn handling of HTTP errors"""
        # Create valid test request
        test_request = ChatRequest(sequence_id=1, continuation_token=None, payload=ChatMessage(message="Test message"))

        # Reset mock and setup error
        mock_chat_requester.request_stream.reset_mock()
        mock_chat_requester.request_stream.side_effect = requests.HTTPError(
            "Server error",
            response=mocker.Mock(spec=requests.Response),
        )

        # Get the generator
        response_generator = dba_chat_client.turn(test_request)

        # Verify error handling
        with pytest.raises(requests.HTTPError) as exc_info:
            next(response_generator)  # Trigger generator execution

        assert "Server error" in str(exc_info.value)
        mock_chat_requester.request_stream.assert_called_once_with(
            f"{CRYSTAL_API_URL}{API_ENDPOINTS['CHAT_CONTINUE'].format(thread_id=dba_chat_client.thread_id)}", test_request
        )

    def test_turn_with_empty_message(self, dba_chat_client, mock_chat_requester):
        """Test chat turn with empty message"""
        # Reset mock to clear initialization call
        mock_chat_requester.request.reset_mock()

        # Create test request
        test_request = ChatRequest(sequence_id=1, continuation_token=None, payload=ChatMessage(message=""))

        # Setup mock response
        mock_response = ChatResponse(
            sequence_id=1,
            continuation_token="token123",
            payload=ChatMessageFragment(message_fragment=""),
        ).model_dump_json()
        mock_chat_requester.request_stream.return_value = iter([mock_response])

        # Execute turn
        response_generator = dba_chat_client.turn(test_request)
        responses = list(response_generator)

        # Verify response
        assert all(isinstance(r, ChatResponse) for r in responses)
        assert isinstance(responses[0].payload, ChatMessageFragment)
        assert responses[0].payload.message_fragment == ""
        assert responses[0].sequence_id == 1
        assert responses[0].continuation_token == "token123"
        assert len(responses) == 1
