import logging
import os

import pytest
from pytest import raises
from pytest_mock import MockerFixture

from crystaldba.cli.main import main
from crystaldba.cli.parse_args import get_database_url
from crystaldba.cli.parse_args import get_log_level
from crystaldba.cli.parse_args import parse_args


class TestArgumentParsing:
    def test_default_args(self, mocker: MockerFixture):
        """Test default argument values"""
        mocker.patch("sys.argv", ["crystaldba"])
        args, _ = parse_args()
        assert args.dburi is None
        assert args.profile == "default"
        assert args.verbose == 0
        assert not hasattr(args, "help")
        # TODO parsed arguments have changed should add them here.

    def test_all_args(self, mocker: MockerFixture):
        """Test parsing all possible arguments"""
        mocker.patch(
            "sys.argv",
            [
                "crystaldba",
                "postgresql://user:pass@localhost/testdb",
                "--profile",
                "test_profile",
                "-vv",
                "-h",
                "testhost",
                "-p",
                "5433",
                "-U",
                "testuser",
                "-d",
                "otherdb",
            ],
        )
        args, _ = parse_args()

        # Test all possible arguments from parse_args()
        assert args.dburi == "postgresql://user:pass@localhost/testdb"
        assert args.profile == "test_profile"
        assert args.verbose == 2
        assert args.host == "testhost"
        assert args.port == "5433"
        assert args.username == "testuser"
        assert args.dbname == "otherdb"
        assert not hasattr(args, "help")  # Help is suppressed

        # Test that all argument groups are present
        # Connection options group
        assert hasattr(args, "dburi")
        assert hasattr(args, "host")
        assert hasattr(args, "port")
        assert hasattr(args, "username")
        assert hasattr(args, "dbname")

        # Other options group
        assert hasattr(args, "profile")
        assert hasattr(args, "verbose")

    def test_well_formed_url(self, mocker: MockerFixture):
        """Test parsing a well-formed PostgreSQL URL"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost:5432/dbname"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "password"
        assert db_url.host == "localhost"
        assert db_url.port == 5432
        assert db_url.database == "dbname"
        assert db_url.query == {}

    def test_url_without_credentials(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL without username and password"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://myhost/dbname"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "prompted_password")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "postgres"  # Default username
        assert db_url.password == "prompted_password"
        assert db_url.host == "myhost"
        assert db_url.port == 5432  # Default port
        assert db_url.database == "dbname"
        assert db_url.query == {}

    def test_url_without_password(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL with username but no password"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user@localhost:5432/dbname"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "prompted_password")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "prompted_password"
        assert db_url.host == "localhost"
        assert db_url.port == 5432
        assert db_url.database == "dbname"
        assert db_url.query == {}

    def test_url_with_ipv6_host(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL with IPv6 address as host"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@[::1]:5432/dbname"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "password"
        assert db_url.host == "::1"
        assert db_url.port == 5432
        assert db_url.database == "dbname"
        assert db_url.query == {}

    def test_url_with_ssl_mode(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL with sslmode parameter"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost:5432/dbname?sslmode=require"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "password"
        assert db_url.host == "localhost"
        assert db_url.port == 5432
        assert db_url.database == "dbname"
        assert db_url.query == {"sslmode": "require"}

    def test_url_with_multiple_query_params(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL with multiple query parameters"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost:5432/dbname?sslmode=verify-full&application_name=myapp&connect_timeout=10"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "password"
        assert db_url.host == "localhost"
        assert db_url.port == 5432
        assert db_url.database == "dbname"
        assert db_url.query == {
            "sslmode": "verify-full",
            "application_name": "myapp",
            "connect_timeout": "10",
        }

    def test_url_with_unix_socket(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL with Unix socket path"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@%2Fvar%2Frun%2Fpostgresql/dbname"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "password"
        assert db_url.host == "/var/run/postgresql"
        assert db_url.port is None
        assert db_url.database == "dbname"
        assert db_url.query == {}

    def test_url_without_port(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL without port specification"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost/dbname"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "password"
        assert db_url.host == "localhost"
        assert db_url.port == 5432  # Should use default port
        assert db_url.database == "dbname"
        assert db_url.query == {}

    def test_url_with_special_chars(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL with special characters in credentials"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://us%24r:pa%23sword@localhost:5432/dbname"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "us$r"  # Decoded from percent encoding
        assert db_url.password == "pa#sword"  # Decoded from percent encoding
        assert db_url.host == "localhost"
        assert db_url.port == 5432
        assert db_url.database == "dbname"
        assert db_url.query == {}

    def test_url_with_empty_query(self, mocker: MockerFixture):
        """Test parsing a PostgreSQL URL with empty query parameters"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost:5432/dbname?"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "password"
        assert db_url.host == "localhost"
        assert db_url.port == 5432
        assert db_url.database == "dbname"
        assert db_url.query == {}

    def test_invalid_username_chars(self, mocker: MockerFixture):
        """Test rejection of invalid characters in username"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://bad!user:password@localhost/dbname"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Username contains invalid characters"):
            get_database_url(args, lambda: "INVALID")

    def test_invalid_database_chars(self, mocker: MockerFixture):
        """Test rejection of invalid characters in database name"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost/bad;dbname"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Database name contains invalid characters"):
            get_database_url(args, lambda: "INVALID")

    def test_invalid_port(self, mocker: MockerFixture):
        """Test rejection of non-numeric port"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "--host", "localhost", "--port", "abc123"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Port must be a number"):
            get_database_url(args, lambda: "INVALID")

    def test_invalid_host_chars(self, mocker: MockerFixture):
        """Test rejection of invalid characters in hostname"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@bad|host/dbname"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Host contains invalid characters"):
            get_database_url(args, lambda: "INVALID")

    def test_invalid_password_null(self, mocker: MockerFixture):
        """Test rejection of null character in password"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:pass\0word@localhost/dbname"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Password contains invalid characters"):
            get_database_url(args, lambda: "INVALID")

    def test_invalid_query_param_key(self, mocker: MockerFixture):
        """Test rejection of invalid characters in query parameter key"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost/dbname?bad!key=value"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Query parameter bad!key contains invalid characters"):
            get_database_url(args, lambda: "INVALID")

    def test_invalid_query_param_value(self, mocker: MockerFixture):
        """Test rejection of invalid characters in query parameter value"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost/dbname?key=bad!value"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Query parameter value 'bad!value' contains invalid characters"):
            get_database_url(args, lambda: "INVALID")

    def test_invalid_scheme(self, mocker: MockerFixture):
        """Test rejection of invalid URL scheme"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "mysql://user:password@localhost/dbname"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Unsupported protocol in database URI"):
            get_database_url(args, lambda: "INVALID")

    def test_invalid_port_in_url(self, mocker: MockerFixture):
        """Test rejection of non-numeric port in URL"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost:abc123/dbname"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Port could not be cast to integer value"):
            get_database_url(args, lambda: "INVALID")

    def test_empty_database(self, mocker: MockerFixture):
        """Test rejection of empty database name"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost/"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "user"
        assert db_url.password == "password"
        assert db_url.host == "localhost"
        assert db_url.port == 5432
        assert db_url.database == "user"
        assert db_url.query == {}

    def test_invalid_multiple_query_params(self, mocker: MockerFixture):
        """Test rejection of invalid characters in multiple query parameters"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:password@localhost/dbname?valid=ok&bad!key=value"],
        )
        args, _ = parse_args()

        with raises(ValueError, match="Query parameter bad!key contains invalid characters"):
            get_database_url(args, lambda: "INVALID")

    def test_no_parameters_raises_error(self, mocker: MockerFixture):
        """Test that no parameters raises an error"""

        mocker.patch.dict(os.environ, clear=True)
        mocker.patch("sys.argv", ["crystaldba"])
        args, _ = parse_args()

        with raises(ValueError, match=r"Must provide database connection credentials."):
            _ = get_database_url(args, lambda: "INVALID")


class TestLogLevel:
    @pytest.mark.parametrize(
        "verbosity,expected_level",
        [
            (0, logging.ERROR),
            (1, logging.INFO),
            (2, logging.DEBUG),
            (3, logging.DEBUG),
        ],
    )
    def test_log_level_selection(self, verbosity, expected_level):
        """Test log level selection based on verbosity"""
        assert get_log_level(verbosity) == expected_level

    def test_failed_database_connection(self, capsys, mocker: MockerFixture):
        """Test handling of failed database connection"""
        mocker.patch("crystaldba.cli.main.LocalSqlDriver", side_effect=Exception("Connection failed"))
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch("crystaldba.cli.main.Console")
        mocker.patch("sys.argv", ["crystaldba"])
        with pytest.raises(SystemExit) as exc_info:
            main()

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert "Oops! I was unable to connect to the database" in captured.out

    def test_help_flag(self, capsys, mocker: MockerFixture):
        """Test --help flag displays help text"""
        mocker.patch("sys.argv", ["crystaldba", "--help"])
        with raises(SystemExit) as exc_info:
            main()

        captured = capsys.readouterr()
        assert exc_info.value.code == 0
        assert "Crystal DBA is an AI-powered postgreSQL expert" in captured.out
        assert "usage:" in captured.out
        assert "Connection options:" in captured.out

    def test_no_database_with_defaults(self, mocker: MockerFixture):
        """Test program uses default values when no database is specified"""
        mocker.patch.dict(os.environ, {}, clear=True)
        mocker.patch("sys.argv", ["crystaldba", "mydatabase"])
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "test_password")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "postgres"  # Default username
        assert db_url.password == "test_password"  # Prompted password
        assert db_url.host == "localhost"  # Default host
        assert db_url.port == 5432  # Default port
        assert db_url.database == "mydatabase"

    def test_no_database_with_defaults_and_host(self, mocker: MockerFixture):
        """Test program uses default values when no database is specified"""
        mocker.patch.dict(os.environ, {}, clear=True)
        mocker.patch("sys.argv", ["crystaldba", "--host", "myhost"])
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "test_password")
        assert db_url.drivername == "postgresql"
        assert db_url.username == "postgres"  # Default username
        assert db_url.password == "test_password"  # Prompted password
        assert db_url.host == "myhost"  # Default host
        assert db_url.port == 5432  # Default port
        assert db_url.database == "postgres"

    def test_conflicting_connection_parameters(self, mocker: MockerFixture):
        """Test that command line parameters override URI parameters when both are provided"""
        mocker.patch(
            "sys.argv",
            ["crystaldba", "postgresql://user:pass@localhost:5432/testdb", "-h", "otherhost", "-p", "5433", "-U", "otheruser", "-d", "otherdb"],
        )
        args, _ = parse_args()

        db_url = get_database_url(args, lambda: "INVALID")
        # Command line parameters should take precedence
        assert db_url.host == "otherhost"
        assert db_url.port == 5433
        assert db_url.username == "otheruser"
        assert db_url.database == "otherdb"
        # Password from URI should be preserved since no password flag exists
        assert db_url.password == "pass"


class TestDatabaseConnection:
    def test_failed_connection(self, capsys, mocker: MockerFixture):
        """Test failed database connection"""
        mocker.patch("crystaldba.cli.main.LocalSqlDriver", side_effect=Exception("Connection failed"))
        mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}, clear=True)
        mocker.patch(
            "sys.argv",
            ["crystaldba"],
        )
        with raises(SystemExit) as exc_info:
            main()

        captured = capsys.readouterr()
        assert exc_info.value.code == 1
        assert "Oops! I was unable to connect to the database" in captured.out


class TestCommandLineArgs:
    def test_verbose_flags(self, mocker: MockerFixture):
        """Test verbose flag sets correct log level"""
        test_cases = [
            (["crystaldba"], logging.ERROR),
            (["crystaldba", "-v"], logging.INFO),
            (["crystaldba", "-vv"], logging.DEBUG),
            (["crystaldba", "-vvv"], logging.DEBUG),
        ]

        for args, expected_level in test_cases:
            mock_log_config = mocker.patch("logging.basicConfig")
            mocker.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@nowhere/test"}, clear=True)
            mocker.patch(
                "sys.argv",
                args,
            )
            mocker.patch("crystaldba.cli.main.LocalSqlDriver", side_effect=Exception("Connection failed"))
            mock_session = mocker.patch("crystaldba.cli.main.PromptSession")
            mock_session.return_value.prompt.side_effect = KeyboardInterrupt
            with raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
            mock_log_config.assert_called_with(level=expected_level, stream=mocker.ANY)
