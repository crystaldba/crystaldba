import os
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from crystaldba.cli.main import main


class TestMainProgram:
    def test_successful_startup(self, mocker: MockerFixture):
        """Test successful program startup and initialization"""
        mock_sql_driver = mocker.Mock()
        mock_profile = mocker.Mock()
        mock_profile.system_id = "test-system-id"
        mock_profile.config_dir = Path("/tmp")

        # Mock all required dependencies
        mocker.patch("crystaldba.cli.main.LocalSqlDriver", return_value=mock_sql_driver)
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.Console")
        mock_session = mocker.patch("crystaldba.cli.main.PromptSession")
        mocker.patch("crystaldba.cli.main.get_or_create_profile", return_value=(mock_profile, mocker.Mock()))
        mock_chat_client = mocker.Mock()
        mocker.patch("crystaldba.cli.main.DbaChatClient", return_value=mock_chat_client)

        mock_session.return_value.prompt.side_effect = KeyboardInterrupt
        main()

    def test_failed_database_connection(self, capsys, mocker: MockerFixture):
        """Test handling of failed database connection"""
        mocker.patch("crystaldba.cli.main.LocalSqlDriver", side_effect=Exception("Connection failed"))
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.Console")

        with pytest.raises(SystemExit) as exc_info:
            main()

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert "Oops! I was unable to connect to the database" in captured.out

    @pytest.mark.parametrize(
        "exit_command",
        ["bye", "quit", "exit", "BYE", "QUIT", "EXIT", "Bye", "Quit", "Exit ", "   eXiT   "],
    )
    def test_exit_commands(self, exit_command, mocker: MockerFixture):
        """Test that exit commands trigger program exit with correct message"""
        mock_console = mocker.Mock()
        mock_prompt = mocker.Mock()
        mock_prompt.prompt.return_value = exit_command

        mock_profile = mocker.Mock()
        mock_profile.system_id = "test-system-id"
        mock_profile.config_dir = Path("/tmp")

        # Set up environment and mocks
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.PromptSession", return_value=mock_prompt)
        mocker.patch("crystaldba.cli.main.Console", return_value=mock_console)
        mocker.patch("crystaldba.cli.main.get_or_create_profile", return_value=(mock_profile, mocker.Mock()))
        mocker.patch("crystaldba.cli.main.LocalSqlDriver")
        mocker.patch("crystaldba.cli.main.DbaChatClient")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        assert "Goodbye" in mock_console.print.call_args[0][0]

    def test_chat_loop(self, mocker: MockerFixture):
        """Test the main chat loop functionality"""
        mock_console = mocker.Mock()
        mock_prompt = mocker.Mock()
        # Simulate user entering a message and then exiting
        mock_prompt.prompt.side_effect = ["test query", "exit"]

        mock_profile = mocker.Mock()
        mock_profile.system_id = "test-system-id"
        mock_profile.config_dir = Path("/tmp")

        mock_chat_loop = mocker.Mock()
        mock_chat_loop.run_to_completion.return_value = iter(["Response to test query"])

        # Set up all required mocks
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.Live")
        mocker.patch("crystaldba.cli.main.PromptSession", return_value=mock_prompt)
        mocker.patch("crystaldba.cli.main.Console", return_value=mock_console)
        mocker.patch("crystaldba.cli.main.get_or_create_profile", return_value=(mock_profile, mocker.Mock()))
        mocker.patch("crystaldba.cli.main.LocalSqlDriver")
        mocker.patch("crystaldba.cli.main.ChatLoop", return_value=mock_chat_loop)
        mocker.patch("crystaldba.cli.main.DbaChatClient")

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Verify chat loop was called with the test query
        mock_chat_loop.run_to_completion.assert_called_once_with("test query")
        assert exc_info.value.code == 0
