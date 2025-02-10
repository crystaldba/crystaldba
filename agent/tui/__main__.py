"""
Elia CLI
"""

import logging

import click
from click_default_group import DefaultGroup
from rich.console import Console

from crystaldba.cli import startup
from tui.app import Elia

# from tui.config import LaunchConfig
# from tui.locations import config_file


console = Console()


# def load_or_create_config_file() -> dict[str, Any]:
#     config = config_file()
#
#     try:
#         file_config = tomllib.loads(config.read_text())
#     except FileNotFoundError:
#         file_config = {}
#         try:
#             config.touch()
#         except OSError:
#             pass
#
#     return file_config


@click.group(cls=DefaultGroup, default="default", default_if_no_args=True)
def cli() -> None:
    """Interact with large language models using your terminal."""


@cli.command()
@click.option(
    "-i",
    "--inline",
    is_flag=True,
    help="Run in inline mode, without launching full TUI.",
    default=False,
)
@click.argument("dburi", nargs=-1, type=str, required=False)
@click.option("--profile", type=str, default="", help="The user profile to use for the chat")
@click.option("-h", "--host", type=str, default="", help='database server host or socket directory (default: "localhost")')
@click.option("-p", "--port", type=int, default=5432, help='database server port (default: "5432")')
@click.option("-U", "-u", "--user", type=str, default="", help='database user name (default: "postgres")')
@click.option("-d", "--dbname", type=str, default="", help='database name (default: "postgres")')
def default(
    inline: bool,
    dburi: tuple[str, ...],
    profile: str,
    host: str,
    port: int,
    user: str,
    dbname: str,
    # prompt: tuple[str, ...],
) -> None:
    chat_turn = startup.startup(
        log_path="log.log",
        logging_level=logging.INFO,
    )
    logger = logging.getLogger(__name__)
    logger.info("starting elia")
    # prompt = ("",)
    # prompt = prompt or ("",)
    # joined_prompt = " ".join(prompt)
    # joined_prompt = ""  # NOTE: this text will be ignored and instead the StartupMessage will occur  # ELIAINFO
    # create_db_if_not_exists()
    # file_config = load_or_create_config_file()
    # cli_config = {}

    app = Elia(chat_turn=chat_turn)
    # launch_config: dict[str, Any] = {**file_config, **cli_config}
    # app = Elia(LaunchConfig(**launch_config), startup_prompt=joined_prompt, chat_turn=chat_turn)
    app.run(inline=inline)


# import asyncio
# import pathlib
# from textwrap import dedent
# from tui.database.database import create_database
# from tui.database.database import sqlite_file_name
# from tui.database.import_chatgpt import import_chatgpt_data
# def create_db_if_not_exists() -> None:
#     if not sqlite_file_name.exists():
#         click.echo(f"Creating database at {sqlite_file_name!r}")
#         asyncio.run(create_database())
# @cli.command()
# def reset() -> None:
#     """
#     Reset the database
#
#     This command will delete the database file and recreate it.
#     Previously saved conversations and data will be lost.
#     """
#     from rich.padding import Padding
#     from rich.text import Text
#
#     console.print(
#         Padding(
#             Text.from_markup(
#                 dedent(f"""\
# [u b red]Warning![/]
#
# [b red]This will delete all messages and chats.[/]
#
# You may wish to create a backup of \
# "[bold blue u]{sqlite_file_name.resolve().absolute()!s}[/]" before continuing.
#             """)
#             ),
#             pad=(1, 2),
#         )
#     )
#     if click.confirm("Delete all chats?", abort=True):
#         sqlite_file_name.unlink(missing_ok=True)
#         asyncio.run(create_database())
#         console.print(f"♻️  Database reset @ {sqlite_file_name}")
#
# @cli.command("import")
# @click.argument(
#     "file",
#     type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path, resolve_path=True),
# )
# def import_file_to_db(file: pathlib.Path) -> None:
#     """
#     Import ChatGPT Conversations
#
#     This command will import the ChatGPT conversations from a local
#     JSON file into the database.
#     """
#     asyncio.run(import_chatgpt_data(file=file))
#     console.print(f"[green]ChatGPT data imported from {str(file)!r}")


if __name__ == "__main__":
    cli()
