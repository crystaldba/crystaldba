"""
Crystal DBA Text UI (TUI)
"""

import logging

import click
from click_default_group import DefaultGroup
from rich.console import Console

from crystaldba.cli import startup
from tui.app import Tui

console = Console()


@click.group(cls=DefaultGroup, default="default", default_if_no_args=True)
def cli() -> None:
    """Your AI teammate with PostgreSQL expertise."""


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
) -> None:
    chat_turn = startup.startup(
        log_path="log.log",
        logging_level=logging.INFO,
    )

    app = Tui(chat_turn=chat_turn)
    app.run(inline=inline)


if __name__ == "__main__":
    cli()
