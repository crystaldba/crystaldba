import logging
import sys
from getpass import getpass

from rich import print
from rich.console import Console

from crystaldba.cli.chat_requester import ChatRequester
from crystaldba.cli.chat_response_followup import ChatResponseFollowup
from crystaldba.cli.chat_turn import ChatTurn
from crystaldba.cli.dba_chat_client import DbaChatClient
from crystaldba.cli.parse_args import get_database_url
from crystaldba.cli.parse_args import get_log_level
from crystaldba.cli.parse_args import parse_args
from crystaldba.cli.profile import get_or_create_profile
from crystaldba.cli.sql_tool import LocalSqlDriver
from crystaldba.shared.constants import get_crystal_api_url


def startup(*, log_path: str = "log.log", logging_level: int = logging.INFO):
    args, parser = parse_args()

    try:
        database_url = get_database_url(args, password_prompt)
    except ValueError as e:
        print(f"\nThere is a problem with your DATABASE_URL. Error: {e}")
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(
        level=get_log_level(logging_level),
        filename=log_path,
        filemode="a",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.info("initial startup")

    screen_console = Console()

    try:
        sql_driver = LocalSqlDriver(
            engine_url=database_url,
            create_engine_params={
                "connect_args": {
                    "options": "-c statement_timeout=10000",  # 10-seconds
                },
            },
        )
        logger.info(f"Connected to database: {database_url}")
    except Exception:
        print(f"Oops! I was unable to connect to the database:\n{database_url}")
        sys.exit(1)

    try:
        profile_obj, http_session = get_or_create_profile(args.profile)
        logger.info(f"Using profile: {args.profile}")
    except Exception as e:
        logger.critical(f"Error getting or creating profile: {e!r}")
        logger.critical("Stack trace:", exc_info=True)
        print(f"ERROR: unable to get or create profile. Is the backend server running at {get_crystal_api_url()}? Error: {e}")
        sys.exit(1)

    screen_console.print("Testing database connection...")
    try:
        sql_driver.local_execute_query_raw("SELECT 1")
        logger.debug("Database connection test successful")
    except Exception as e:
        logger.critical(f"Database connection test failed: {e!r}")
        print("ERROR: Database connection test failed. The database connection appears to be invalid.")
        sys.exit(1)
    screen_console.print("Database connection test successful\n")

    chat_requester = ChatRequester(http_session, screen_console)

    return ChatTurn(
        DbaChatClient(chat_requester),
        ChatResponseFollowup(
            sql_driver,
        ),
    )


def password_prompt() -> str:
    try:
        password = getpass("Database password: ")
        if password is None:
            print("\nPassword is required")
            sys.exit(1)
        return password
    except (KeyboardInterrupt, EOFError):
        print("\nPassword entry cancelled")
        sys.exit(1)
