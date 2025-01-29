import pytest
from pytest_mock import MockerFixture
from rich.console import Console

from crystaldba.cli.chat_loop import ChatLoop
from crystaldba.cli.chat_turn import ChatTurn


class TestChatLoop:
    @pytest.fixture
    def mock_chat_turn(self, mocker: MockerFixture) -> ChatTurn:
        return mocker.Mock(spec=ChatTurn)

    @pytest.fixture
    def mock_prompt_fn(self, mocker: MockerFixture):
        return mocker.Mock()

    @pytest.fixture
    def mock_console(self, mocker: MockerFixture) -> Console:
        return mocker.Mock()

    @pytest.fixture
    def chat_loop(self, mock_chat_turn, mock_prompt_fn, mock_console):
        return ChatLoop(
            chat_turn=mock_chat_turn,
            prompt_fn=mock_prompt_fn,
            screen_console=mock_console,
            initial_messages=[],
        )

    def test_displays_initial_help_text(self, chat_loop, mock_console, mock_prompt_fn):
        """Test that the initial help text is displayed"""
        mock_prompt_fn.side_effect = KeyboardInterrupt
        chat_loop.chat_loop()

        # Verify help text was printed
        assert mock_console.print.call_args[0][0].startswith("What can I help you with?")

    @pytest.mark.parametrize(
        "exit_command",
        ["bye", "quit", "exit", "BYE", "QUIT", "EXIT", "Bye", "Quit", "Exit"],
    )
    def test_exit_commands(self, exit_command, chat_loop, mock_console, mock_prompt_fn):
        """Test that exit commands trigger program exit with correct message"""
        mock_prompt_fn.return_value = exit_command

        with pytest.raises(SystemExit) as exc_info:
            chat_loop.chat_loop()

        assert exc_info.value.code == 0
        assert "Goodbye" in mock_console.print.call_args[0][0]

    def test_empty_input_continues_loop(self, chat_loop, mock_prompt_fn, mock_chat_turn):
        """Test that empty input continues the loop without processing"""
        mock_prompt_fn.side_effect = ["", "exit"]

        with pytest.raises(SystemExit):
            chat_loop.chat_loop()

        # Verify chat turn wasn't called for empty input
        mock_chat_turn.run_to_completion.assert_not_called()

    def test_processes_valid_input(self, chat_loop, mock_prompt_fn, mock_chat_turn, mocker: MockerFixture):
        """Test that valid input is processed correctly"""
        test_input = "test query"
        test_response = "Response to test query"
        mock_prompt_fn.side_effect = [test_input, "exit"]
        mock_chat_turn.run_to_completion.return_value = iter([test_response])
        mocker.patch("crystaldba.cli.chat_loop.Live")

        with pytest.raises(SystemExit):
            chat_loop.chat_loop()

        mock_chat_turn.run_to_completion.assert_called_once_with(test_input)

    def test_handles_keyboard_interrupt(self, chat_loop, mock_prompt_fn):
        """Test that KeyboardInterrupt exits gracefully"""
        mock_prompt_fn.side_effect = KeyboardInterrupt

        # Should complete without raising
        chat_loop.chat_loop()
