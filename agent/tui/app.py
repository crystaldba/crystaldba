from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from textual.app import App
from textual.binding import Binding
from textual.binding import BindingType

from tui.models import ChatData
from tui.models import ChatMessage
from tui.screens.chat_screen import ChatScreen
from tui.screens.help_screen import HelpScreen

if TYPE_CHECKING:
    from litellm.types.completion import ChatCompletionSystemMessageParam
    from litellm.types.completion import ChatCompletionUserMessageParam


class Tui(App[None]):
    ENABLE_COMMAND_PALETTE: ClassVar[bool] = False
    CSS_PATH = Path(__file__).parent / "tui.scss"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "app.quit", "Quit", show=False),
        Binding("f1,?", "help", "Help"),
    ]

    def __init__(
        self,
        chat_turn: Any = None,
    ):
        self.chat_turn = chat_turn

        super().__init__()

    async def on_mount(self) -> None:
        await self.launch_chat()

    async def launch_chat(
        self,
    ) -> None:
        current_time = datetime.datetime.now(datetime.timezone.utc)
        system_message: ChatCompletionSystemMessageParam = {
            "content": "",
            "role": "system",
        }
        user_message: ChatCompletionUserMessageParam = {
            "content": "",
            "role": "user",
        }
        chat = ChatData(
            id=None,
            title=None,
            create_timestamp=None,
            messages=[
                ChatMessage(
                    message=system_message,
                    timestamp=current_time,
                ),
                ChatMessage(
                    message=user_message,
                    timestamp=current_time,
                ),
            ],
        )
        chat.id = -1
        await self.push_screen(ChatScreen(chat))

    async def action_help(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        else:
            await self.push_screen(HelpScreen())

    def get_css_variables(self) -> dict[str, str]:
        color_system = {}

        return {**super().get_css_variables(), **color_system}


if __name__ == "__main__":
    app = Tui()
    app.run()
