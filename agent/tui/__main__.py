"""
Crystal DBA Text UI (TUI)
"""

import logging

from rich.console import Console

from crystaldba.cli import startup
from tui.app import Tui

console = Console()


def cli() -> None:
    chat_turn = startup.startup(
        log_path="log.log",
        logging_level=logging.INFO,
    )

    app = Tui(chat_turn=chat_turn)
    app.run(inline=False)


if __name__ == "__main__":
    cli()
