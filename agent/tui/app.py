from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from textual.app import App
from textual.binding import Binding
from textual.binding import BindingType
from textual.reactive import Reactive
from textual.reactive import reactive

from tui.models import ChatData
from tui.models import ChatMessage
from tui.screens.chat_screen import ChatScreen
from tui.screens.help_screen import HelpScreen
from tui.themes import BUILTIN_THEMES
from tui.themes import Theme
from tui.themes import load_user_themes

# from textual.signal import Signal
# from tui.chats_manager import ChatsManager
# from tui.config import EliaChatModel
# from tui.config import LaunchConfig
# from tui.runtime_config import RuntimeConfig

if TYPE_CHECKING:
    from litellm.types.completion import ChatCompletionSystemMessageParam
    from litellm.types.completion import ChatCompletionUserMessageParam


class Elia(App[None]):
    # launch_config: LaunchConfig
    ENABLE_COMMAND_PALETTE: ClassVar[bool] = False
    CSS_PATH = Path(__file__).parent / "elia.scss"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "app.quit", "Quit", show=False),
        Binding("f1,?", "help", "Help"),
    ]

    def __init__(
        self,
        # config: LaunchConfig,
        # startup_prompt: str = "",
        chat_turn: Any = None,
    ):
        # self.launch_config = config
        self.chat_turn = chat_turn

        available_themes: dict[str, Theme] = BUILTIN_THEMES.copy()
        available_themes |= load_user_themes()

        self.themes: dict[str, Theme] = available_themes

        # self._runtime_config = RuntimeConfig(
        #     selected_model=config.default_model_object,
        #     system_prompt=config.system_prompt,
        # )
        # self.runtime_config_signal = Signal[RuntimeConfig](self, "runtime-config-updated")
        # """Widgets can subscribe to this signal to be notified of
        # when the user has changed configuration at runtime (e.g. using the UI)."""
        # self.startup_prompt = startup_prompt
        # """Elia can be launched with a prompt on startup via a command line option.
        #
        # This is a convenience which will immediately load the chat interface and
        # put users into the chat window, rather than going to the home screen.
        # """

        super().__init__()

    theme: Reactive[str | None] = reactive(None, init=False)

    # @property
    # def runtime_config(self) -> RuntimeConfig:
    #     return self._runtime_config

    # @runtime_config.setter
    # def runtime_config(self, new_runtime_config: RuntimeConfig) -> None:
    #     self._runtime_config = new_runtime_config
    #     self.runtime_config_signal.publish(self.runtime_config)

    async def on_mount(self) -> None:
        # from tui.screens.home_screen import HomeScreen # ELIAINFO
        # await self.push_screen(HomeScreen(self.runtime_config_signal))
        # self.theme = self.launch_config.theme
        # if self.startup_prompt:  # ELIAINFO
        await self.launch_chat(
            # prompt=self.startup_prompt,
            # model=self.runtime_config.selected_model,
        )

    async def launch_chat(
        self,
        # prompt: str,
        # model: EliaChatModel,
    ) -> None:
        current_time = datetime.datetime.now(datetime.timezone.utc)
        system_message: ChatCompletionSystemMessageParam = {
            "content": "",
            # "content": self.runtime_config.system_prompt,
            "role": "system",
        }
        user_message: ChatCompletionUserMessageParam = {
            "content": "",
            # "content": prompt,
            "role": "user",
        }
        chat = ChatData(
            id=None,
            title=None,
            create_timestamp=None,
            # model=model,
            messages=[
                ChatMessage(
                    message=system_message,
                    timestamp=current_time,
                    # model=model,
                ),
                ChatMessage(
                    message=user_message,
                    timestamp=current_time,
                    # model=model,
                ),
            ],
        )
        # chat.id = await ChatsManager.create_chat(chat_data=chat)
        chat.id = -1
        await self.push_screen(ChatScreen(chat))

    async def action_help(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        else:
            await self.push_screen(HelpScreen())

    def get_css_variables(self) -> dict[str, str]:
        if self.theme:
            theme = self.themes.get(self.theme)
            if theme:
                color_system = theme.to_color_system().generate()
            else:
                color_system = {}
        else:
            color_system = {}

        return {**super().get_css_variables(), **color_system}

    def watch_theme(self, theme: str | None) -> None:
        self.refresh_css(animate=False)
        self.screen._update_styles()

    @property
    def theme_object(self) -> Theme | None:
        if self.theme is None:
            return None
        try:
            return self.themes[self.theme]
        except KeyError:
            return None


if __name__ == "__main__":
    app = Elia()
    # app = Elia(LaunchConfig())
    app.run()
