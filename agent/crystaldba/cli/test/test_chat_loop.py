import pytest
from pytest_mock import MockerFixture
from rich.console import Console

from crystaldba.cli.chat_loop import ChatLoop
from crystaldba.cli.chat_loop import ChatLoopExit
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
        """Default chat loop with empty initial messages"""
        return ChatLoop(
            chat_turn=mock_chat_turn,
            prompt_fn=mock_prompt_fn,
            screen_console=mock_console,
            initial_messages=[],
        )

    @pytest.fixture
    def chat_loop_with_messages(self, mock_chat_turn, mock_prompt_fn, mock_console):
        """Helper fixture to create chat loop with specific initial messages"""

        def _create_chat_loop(messages):
            return ChatLoop(
                chat_turn=mock_chat_turn,
                prompt_fn=mock_prompt_fn,
                screen_console=mock_console,
                initial_messages=messages,
            )

        return _create_chat_loop

    def test_displays_initial_help_text(self, mock_chat_turn, mock_prompt_fn, mock_console, mocker: MockerFixture):
        """Test that the initial help text is displayed"""
        chat_loop = ChatLoop(
            chat_turn=mock_chat_turn,
            prompt_fn=mock_prompt_fn,
            screen_console=mock_console,
            initial_messages=["SYSTEM: start"],
        )
        mocker.patch("crystaldba.cli.chat_loop.Live")
        mock_chat_turn.run_to_completion.return_value = iter([])
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

        result = chat_loop.chat_loop()

        assert result == ChatLoopExit.BYE
        assert "Goodbye" in mock_console.print.call_args[0][0]

    def test_empty_input_continues_loop(self, chat_loop, mock_prompt_fn, mock_chat_turn):
        """Test that empty input continues the loop without processing"""
        mock_prompt_fn.side_effect = ["", "exit"]

        result = chat_loop.chat_loop()

        assert result == ChatLoopExit.BYE

        # Verify chat turn wasn't called for empty input
        mock_chat_turn.run_to_completion.assert_not_called()

    def test_processes_valid_input(self, chat_loop, mock_prompt_fn, mock_chat_turn, mocker: MockerFixture):
        """Test that valid input is processed correctly"""
        test_input = "test query"
        test_response = "Response to test query"
        mock_prompt_fn.side_effect = [test_input, "exit"]
        mock_chat_turn.run_to_completion.return_value = iter([test_response])
        mocker.patch("crystaldba.cli.chat_loop.Live")

        result = chat_loop.chat_loop()

        assert result == ChatLoopExit.BYE

        mock_chat_turn.run_to_completion.assert_called_once_with(test_input)

    def test_handles_keyboard_interrupt(self, chat_loop, mock_prompt_fn):
        """Test that KeyboardInterrupt exits gracefully"""
        mock_prompt_fn.side_effect = KeyboardInterrupt

        result = chat_loop.chat_loop()
        assert result == ChatLoopExit.KEYBOARD_INTERRUPT

    def test_handles_unknown_exception(self, chat_loop, mock_prompt_fn, mock_chat_turn):
        """Test that unknown exceptions are handled properly"""
        mock_prompt_fn.side_effect = Exception("Unexpected error")

        result = chat_loop.chat_loop()
        assert result == ChatLoopExit.UNKNOWN_EXCEPTION

    def test_processes_initial_messages(self, mock_chat_turn, mock_prompt_fn, mock_console, mocker: MockerFixture):
        """Test that initial messages are processed in order before prompting for input"""
        test_messages = ["Test 1", "exit"]
        chat_loop = ChatLoop(
            chat_turn=mock_chat_turn,
            prompt_fn=mock_prompt_fn,
            screen_console=mock_console,
            initial_messages=test_messages.copy(),
        )

        mock_chat_turn.run_to_completion.return_value = iter(["Response"])
        mocker.patch("crystaldba.cli.chat_loop.Live")

        result = chat_loop.chat_loop()

        assert result == ChatLoopExit.BYE
        # Verify first message was processed
        mock_chat_turn.run_to_completion.assert_called_once_with("Test 1")
        # Verify we never needed to prompt for input
        mock_prompt_fn.assert_not_called()
