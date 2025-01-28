import argparse
import logging
import os
import re
from typing import Callable
from typing import Mapping
from typing import Sequence
from urllib.parse import parse_qs
from urllib.parse import unquote
from urllib.parse import urlparse

from sqlalchemy import URL


def parse_args():
    parser = argparse.ArgumentParser(
        prog="crystaldba",
        description="Crystal DBA is an AI-powered postgreSQL expert.\n\n"
        "Examples:\n"
        "  crystaldba dbname\n"
        "  crystaldba postgres://<username>:<password>@<host>:<port>/<dbname>\n"
        "  crystaldba -d dbname -u dbuser",
        epilog="Contact us:\n  Email support@crystaldba.ai if you have questions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        conflict_handler="resolve",
        add_help=False,
    )

    # Connection options group
    conn_group = parser.add_argument_group("Connection options")
    conn_group.add_argument("dburi", nargs="?", metavar="DBNAME | URI", help="database name or URI to connect to")
    conn_group.add_argument("-h", "--host", metavar="HOSTNAME", help='database server host or socket directory (default: "localhost")')
    conn_group.add_argument("-p", "--port", metavar="PORT", help='database server port (default: "5432")')
    conn_group.add_argument("-U", "-u", "--username", metavar="USERNAME", help='database user name (default: "postgres")')
    conn_group.add_argument("-d", "--dbname", metavar="DBNAME", help='database name (default: "postgres")')

    # Other options group
    other_group = parser.add_argument_group("Other options")
    other_group.add_argument("--profile", default="default", help=argparse.SUPPRESS)
    other_group.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity level (-v: INFO, -vv: DEBUG)")
    other_group.add_argument("--help", action="help", default=argparse.SUPPRESS, help="show this help message and exit")

    return parser.parse_args(), parser


def get_database_url(args: argparse.Namespace, password_prompt: Callable[[], str]) -> URL:
    # Keep track of whether the host was provided. If not we will raise an error
    # rather than prompting for a password.
    conn_info_provided = False

    def find_param(arg_name: str | None, env_name: str, defaults: list[str | None] | None = None) -> str | None:
        result = (getattr(args, arg_name) if arg_name else None) or os.environ.get(env_name)
        if result is None:
            if defaults:
                for default_value in defaults:
                    if default_value is not None:
                        return default_value
            return None
        else:
            nonlocal conn_info_provided
            conn_info_provided = True
            return result.strip()

    conn_username = None
    conn_password = None
    conn_host = None
    conn_port = None
    conn_database = None
    conn_qs = None

    # args.dburi is the first argument and could either be a database name or a database URI
    # detect the dburi case first
    db_uri = find_param("dburi", "DATABASE_URL", [])
    if db_uri and re.match(r"^[a-z]+://", db_uri):
        # Check if protocol is supported after matching
        if not db_uri.startswith(("postgresql://", "postgres://")):
            raise ValueError("Unsupported protocol in database URI. Must be postgresql:// or postgres://")
        parsed_url = urlparse(db_uri)
        if not (parsed_url.scheme == "postgresql" or parsed_url.scheme == "postgres"):
            raise ValueError(f"Error in database URI: {parsed_url.scheme} is not a valid scheme")
        if parsed_url.username:
            conn_username = unquote(parsed_url.username)
        if parsed_url.password:
            conn_password = unquote(parsed_url.password)
        if parsed_url.hostname:
            conn_host = unquote(parsed_url.hostname)
        if parsed_url.port:
            conn_port = str(parsed_url.port)
        if parsed_url.path:
            conn_database = parsed_url.path.lstrip("/")
        if parsed_url.query is not None:  # Check if query exists, even if empty
            conn_qs = None if not parsed_url.query.strip() else parsed_url.query
    else:
        conn_database = args.dburi

    # Fill from environment variables, etc.
    conn_username = find_param("username", "PGUSER", [conn_username, "postgres"])
    conn_password = find_param(None, "PGPASSWORD", [conn_password])
    conn_host = find_param("host", "PGHOST", [conn_host, "localhost"])
    # Don't set default port if using Unix socket path
    if conn_host and conn_host.startswith("/"):
        conn_port = find_param("port", "PGPORT", [conn_port])
    else:
        conn_port = find_param("port", "PGPORT", [conn_port, "5432"])
    conn_database = find_param("dbname", "PGDATABASE", [conn_database if conn_database != "" else None, conn_username])
    conn_qs = find_param(None, "PGOPTIONS", [conn_qs])

    if conn_password is None:
        if conn_info_provided:
            conn_password = password_prompt()
        else:
            raise ValueError("Must provide database connection credentials.")

    # Check required parameters and raise appropriate errors
    if not conn_username:
        raise ValueError("Database username is required")
    if not conn_host:
        raise ValueError("Database host is required")
    if not conn_database:
        raise ValueError("Database name is required")

    # Validate all of the parameters using regular expressions
    if not re.match(r"^[a-zA-Z0-9$#@_.-]+$", conn_username):
        raise ValueError("Username contains invalid characters")
    # No validation needed for password - SQLAlchemy will handle escaping/encoding
    if conn_password is not None and "\0" in str(conn_password):
        raise ValueError("Password contains invalid characters")
    # Allow Unix socket paths (including percent-encoded chars) and IPv6 addresses in hostname
    if not re.match(r"^[a-zA-Z0-9._:/%\-]+$", conn_host):
        raise ValueError("Host contains invalid characters")
    if conn_port and not re.match(r"^\d+$", str(conn_port)):
        raise ValueError("Port must be a number")
    if not re.match(r"^[a-zA-Z0-9_-]+$", conn_database):
        raise ValueError("Database name contains invalid characters")

    conn_query: Mapping[str, Sequence[str] | str] = {}
    if conn_qs and conn_qs.strip():  # Only parse if query string exists and is not empty
        parsed_qs = parse_qs(conn_qs)
        if len(parsed_qs) > 0:
            # Convert query parameter values from lists to single strings
            conn_query = {k: v[0] for k, v in parsed_qs.items()}
            # Validate the query parameters
            for key, value in conn_query.items():
                if not re.match(r"^[a-zA-Z0-9_-]+$", key):
                    raise ValueError(f"Query parameter {key} contains invalid characters")
                # Allow more characters in query parameter values
                if not re.match(r"^[a-zA-Z0-9_.-]+$", str(value)):
                    raise ValueError(f"Query parameter value '{value}' contains invalid characters")

    return URL.create(
        "postgresql",
        username=conn_username,
        password=conn_password,
        host=conn_host,
        port=int(conn_port) if conn_port else None,
        database=conn_database,
        query=conn_query,
    )


def get_log_level(verbosity):
    if verbosity >= 2:
        return logging.DEBUG
    elif verbosity == 1:
        return logging.INFO
    return logging.ERROR
