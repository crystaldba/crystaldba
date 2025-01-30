import logging
import sys
from typing import Iterator
from typing import List
from typing import Protocol

from rich import print
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner


logger = logging.getLogger(__name__)

class ChatTurnProtocol(Protocol):
    def run_to_completion(self, message: str) -> Iterator[str]: ...


class PromptProtocol(Protocol):
    def __call__(self, prompt: str) -> str: ...


class ChatLoop:
    def __init__(
        self,
        chat_turn: ChatTurnProtocol,
        prompt_fn: PromptProtocol,
        screen_console: Console,
        initial_messages: List[str],
    ):
        self.chat_turn = chat_turn
        self.initial_messages = initial_messages
        self.prompt_fn = prompt_fn
        self.screen_console = screen_console

    def chat_loop(self):
        try:
            loop_count = 0
            while True:
                try:
                    if loop_count == 0:
                        message_input = "SYSTEM: start a thread"
                        # TODO, pull messages from self.initial_messages instead of hardcoding one here.
                    else:
                        logger.debug("CLIENT_Main_loop_once: start")
                        message_input = self.prompt_fn("\n> ").strip()
                        self.screen_console.print()
                        if not message_input:
                            continue
                        if message_input.lower().strip() in ["bye", "quit", "exit"]:
                            self.screen_console.print("Goodbye! I'm always available, if you need any further assistance.")
                            sys.exit(0)

                    with Live(
                        Spinner("dots", text="Thinking..."),
                        console=self.screen_console,
                        refresh_per_second=10,
                        vertical_overflow="visible",
                    ) as live:
                        buffer = ""
                        for chunk in self.chat_turn.run_to_completion(message_input):
                            buffer += chunk
                            live.update(Markdown(buffer))
                        buffer += "\n   "
                        live.update(Markdown(buffer))

                except (KeyboardInterrupt, EOFError):
                    break
                loop_count += 1
        except Exception as e:
            logger.critical(f"Error running chat loop: {e!r}", exc_info=True)
            print(f"CRITICAL: Error running chat loop: {e!s}")
            print("\nStack trace:")
            import traceback

            print("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            sys.exit(1)
