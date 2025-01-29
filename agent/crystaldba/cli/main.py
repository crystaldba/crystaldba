import logging
import sys
from getpass import getpass

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich import print
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner

from crystaldba.cli.chat_loop import ChatLoop
from crystaldba.cli.chat_requester import ChatRequester
from crystaldba.cli.chat_response_followup import ChatResponseFollowup
from crystaldba.cli.dba_chat_client import DbaChatClient
from crystaldba.cli.parse_args import get_database_url
from crystaldba.cli.parse_args import get_log_level
from crystaldba.cli.parse_args import parse_args
from crystaldba.cli.profile import get_or_create_profile
from crystaldba.cli.sql_tool import LocalSqlDriver
from crystaldba.shared.constants import CRYSTAL_API_URL


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


def main():
    args, parser = parse_args()

    try:
        database_url = get_database_url(args, password_prompt)
    except ValueError as e:
        print(f"\nError: {e}")
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(level=get_log_level(args.verbose), stream=sys.stderr)
    logger = logging.getLogger(__name__)

    screen_console = Console()

    try:
        sql_driver = LocalSqlDriver(engine_url=database_url)
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
        print(f"ERROR: unable to get or create profile. Is the backend server running at {CRYSTAL_API_URL}? Error: {e}")
        sys.exit(1)

    chat_requester = ChatRequester(http_session, screen_console)

    user_input = PromptSession(
        history=FileHistory(profile_obj.config_dir / "history.txt"),
        enable_suspend=True,  # Allow Ctrl+Z suspension
        wrap_lines=True,  # Wrap long lines
    )

    screen_console.print("Testing database connection...")
    try:
        sql_driver.local_execute_query_raw("SELECT 1")
        logger.debug("Database connection test successful")
    except Exception as e:
        logger.critical(f"Database connection test failed: {e!r}")
        print("ERROR: Database connection test failed. The database connection appears to be invalid.")
        sys.exit(1)
    screen_console.print("Database connection test successful\n")

    screen_console.print(
        "What can I help you with?  A few ideas:\n\n"
        "• Give an overview of the schema\n"
        "• Find the slowest queries\n"
        "• Report on database health\n"
        "• Explain a query plan\n"
        "• Optimize indexes and queries\n"
        "• Generate queries to answer questions"
    )

    try:
        chatloop = ChatLoop(
            user_input,
            screen_console,
            DbaChatClient(chat_requester),
            ChatResponseFollowup(
                screen_console,
                sql_driver,
            ),
        )

        while True:
            try:
                logger.debug("CLIENT_Main_loop_once: start")
                message_input = user_input.prompt("\n> ").strip()
                screen_console.print()
                if message_input.lower() in ["bye", "quit", "exit"]:
                    screen_console.print("Goodbye! I'm always available, if you need any further assistance.")
                    sys.exit(0)
                if message_input:
                    with Live(
                        Spinner("dots", text="Thinking..."),
                        console=screen_console,
                        refresh_per_second=10,
                        vertical_overflow="visible",
                    ) as live:
                        buffer = ""
                        for chunk in chatloop.run_to_completion(message_input):
                            buffer += chunk
                            live.update(Markdown(buffer))
                        buffer += "\n   "
                        live.update(Markdown(buffer))

            except (KeyboardInterrupt, EOFError):
                break
    except Exception as e:
        logger.critical(f"Error running chat loop: {e!r}", exc_info=True)
        print(f"CRITICAL: Error running chat loop: {e!s}")
        print("\nStack trace:")
        import traceback

        print("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        sys.exit(1)


# # DBA has interface similar to server DbaChat / DbaChatRemote
# class DBA:
#     chat_requester: ChatRequester
#
#     def chat(self, request: ChatRequest) -> ChatResponse:  # will be a generator that yields ChatResponse objects eventually
#         # build current_chatrequest
#         while current_chatrequest is not None:
#             response = self.chat_requester.request(current_chatrequest)
#             current_chatrequest, response_output = self.process_response(response)
#             yield response_output


if __name__ == "__main__":
    main()
