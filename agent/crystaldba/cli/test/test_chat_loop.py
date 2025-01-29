import pytest
from prompt_toolkit import PromptSession
from pytest_mock import MockerFixture
from rich.console import Console

from crystaldba.cli.chat_loop import ChatLoop
from crystaldba.cli.chat_response_followup import ChatResponseFollowupProtocol
from crystaldba.shared.api import DbaChatSyncProtocol


@pytest.fixture
def mock_user_input(mocker: MockerFixture):
    return mocker.Mock(spec=PromptSession)


@pytest.fixture
def mock_console(mocker: MockerFixture):
    console = mocker.Mock(spec=Console)
    # Mock the context manager protocol for console.status()
    status_context = mocker.Mock()
    status_context.__enter__ = mocker.Mock(return_value=None)
    status_context.__exit__ = mocker.Mock(return_value=None)
    console.status.return_value = status_context
    return console


@pytest.fixture
def mock_chat_response_followup(mocker: MockerFixture):
    return mocker.Mock(spec=ChatResponseFollowupProtocol)


@pytest.fixture
def mock_dba_chat_client(mocker: MockerFixture):
    return mocker.Mock(spec=DbaChatSyncProtocol)


@pytest.fixture
def chat_loop(mock_user_input, mock_console, mock_chat_response_followup, mock_dba_chat_client):
    return ChatLoop(
        mock_user_input,
        mock_console,
        mock_dba_chat_client,
        mock_chat_response_followup,
    )


class TestChatLoop:
    def test_run_to_completion_empty_input(self, chat_loop):
        """Test handling of empty input"""
        result = list(chat_loop.run_to_completion(""))
        assert result == []
        chat_loop.chat_response_followup.create_chatrequest.assert_not_called()
        chat_loop.dba_chat_client.turn.assert_not_called()

    def test_run_to_completion_normal_flow(self, chat_loop, mocker: MockerFixture):
        """Test normal message flow with direct string response"""
        chat_request = mocker.Mock()
        chat_response = mocker.Mock()
        expected_result = "Response message"

        chat_loop.chat_response_followup.create_chatrequest.return_value = chat_request
        chat_loop.dba_chat_client.turn.return_value = iter([chat_response])
        chat_loop.chat_response_followup.from_chatresponse_to_possible_new_chatrequest.return_value = expected_result

        result = list(chat_loop.run_to_completion("test message"))
        assert result == [expected_result]
        chat_loop.chat_response_followup.create_chatrequest.assert_called_once_with("test message")
        chat_loop.dba_chat_client.turn.assert_called_once_with(chat_request)

    def test_run_to_completion_with_multiple_continuations(self, chat_loop, mocker: MockerFixture):
        """Test handling multiple continuation messages"""
        initial_request = mocker.Mock()
        continuation_request1 = mocker.Mock()
        continuation_request2 = mocker.Mock()
        response1 = mocker.Mock()
        response2 = mocker.Mock()
        response3 = mocker.Mock()
        expected_result = "Final response"

        chat_loop.chat_response_followup.create_chatrequest.return_value = initial_request
        chat_loop.dba_chat_client.turn.side_effect = [iter([response1]), iter([response2]), iter([response3])]
        chat_loop.chat_response_followup.from_chatresponse_to_possible_new_chatrequest.side_effect = [
            continuation_request1,
            continuation_request2,
            expected_result,
        ]

        result = list(chat_loop.run_to_completion("test message"))
        assert result == [expected_result]
        assert chat_loop.dba_chat_client.turn.call_count == 3
        chat_loop.dba_chat_client.turn.assert_has_calls(
            [
                mocker.call(initial_request),
                mocker.call(continuation_request1),
                mocker.call(continuation_request2),
            ]
        )

    def test_run_to_completion_keyboard_interrupt(self, chat_loop, mocker: MockerFixture):
        """Test handling of keyboard interrupt"""
        chat_request = mocker.Mock()
        chat_loop.chat_response_followup.create_chatrequest.return_value = chat_request
        chat_loop.dba_chat_client.turn.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            # Need to iterate the generator to trigger the exception
            list(chat_loop.run_to_completion("test message"))
            chat_loop.run_to_completion("test message")
