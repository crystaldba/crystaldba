import os
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from rich.console import Console

from crystaldba.cli.main import main


class TestMainProgram:
    @pytest.fixture
    def mock_console(self, mocker: MockerFixture) -> Console:
        console = mocker.Mock(spec=Console)
        # Add required Rich Live attributes
        console.is_jupyter = False
        console.__enter__ = mocker.Mock(return_value=None)
        console.__exit__ = mocker.Mock(return_value=None)
        return console

    def test_successful_startup(self, mocker: MockerFixture, mock_console):
        """Test successful program startup and initialization"""
        mock_sql_driver = mocker.Mock()
        mock_dba_chat_client = mocker.Mock()
        mock_profile = mocker.Mock()
        mock_profile.system_id = "test-system-id"
        mock_profile.config_dir = Path("/tmp")

        # Mock all required dependencies
        mocker.patch("crystaldba.cli.main.LocalSqlDriver", return_value=mock_sql_driver)
        mocker.patch("crystaldba.cli.main.DbaChatClient", return_value=mock_dba_chat_client)
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.Console", return_value=mock_console)
        mock_session = mocker.patch("crystaldba.cli.main.PromptSession")
        mocker.patch("crystaldba.cli.main.get_or_create_profile", return_value=(mock_profile, mocker.Mock()))
        mocker.patch("crystaldba.cli.main.ChatLoop")

        # Simulate keyboard interrupt to exit
        mock_session.return_value.prompt.side_effect = KeyboardInterrupt
        main()

        # Verify initialization messages
        assert any("Database connection test successful" in str(args) for args, _ in mock_console.print.call_args_list)

    def test_failed_database_connection(self, capsys, mocker: MockerFixture, mock_console):
        """Test handling of failed database connection"""
        mocker.patch("crystaldba.cli.main.LocalSqlDriver", side_effect=Exception("Connection failed"))
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.Console", return_value=mock_console)

        with pytest.raises(SystemExit) as exc_info:
            main()

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert "Oops! I was unable to connect to the database" in captured.out

    def test_failed_profile_creation(self, capsys, mocker: MockerFixture, mock_console):
        """Test handling of failed profile creation"""
        mock_sql_driver = mocker.Mock()
        mocker.patch("crystaldba.cli.main.LocalSqlDriver", return_value=mock_sql_driver)
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.Console", return_value=mock_console)
        mocker.patch("crystaldba.cli.main.get_or_create_profile", side_effect=Exception("Failed to create profile"))

        with pytest.raises(SystemExit) as exc_info:
            main()

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert "ERROR: unable to get or create profile" in captured.out

    def test_failed_database_test(self, capsys, mocker: MockerFixture, mock_console):
        """Test handling of failed database connection test"""
        mock_sql_driver = mocker.Mock()
        mock_sql_driver.local_execute_query_raw.side_effect = Exception("Test query failed")

        mocker.patch("crystaldba.cli.main.LocalSqlDriver", return_value=mock_sql_driver)
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.Console", return_value=mock_console)
        mocker.patch("crystaldba.cli.main.get_or_create_profile", return_value=(mocker.Mock(config_dir=Path("/tmp")), mocker.Mock()))

        with pytest.raises(SystemExit) as exc_info:
            main()

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert "ERROR: Database connection test failed" in captured.out
