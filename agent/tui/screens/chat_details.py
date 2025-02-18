from datetime import timezone
from typing import ClassVar
from typing import List
from typing import cast

import humanize
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.containers import Vertical
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label
from textual.widgets import Markdown
from textual.widgets import Rule

from tui.models import ChatData


class ChatDetails(ModalScreen[None]):
    BINDINGS: ClassVar[List[Binding]] = [
        Binding(
            "escape",
            "app.pop_screen",
            "Close",
        )
    ]

    def __init__(
        self,
        chat: ChatData,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.chat = chat
        from tui.app import Elia

        self.elia = cast(Elia, self.app)

    def compose(self) -> ComposeResult:
        chat = self.chat
        with Vertical(id="container") as vs:
            vs.border_title = "Chat details"
            vs.border_subtitle = "(read only)"
            with Horizontal():
                with VerticalScroll(id="left"):
                    content = chat.system_prompt.message.get("content", "")
                    if isinstance(content, str):
                        yield Label("System prompt", classes="heading")
                        yield Markdown(content)

                yield Rule(orientation="vertical")

                with VerticalScroll(id="right"):
                    yield Label("Identifier", classes="heading")
                    yield Label(str(chat.id) or "Unknown", classes="datum")

                    yield Rule()

                    model = chat.model
                    yield Label("Model information", classes="heading")
                    yield Label(model.name, classes="datum")

                    if display_name := model.display_name:
                        yield Label(display_name, classes="datum")
                    if provider := model.provider:
                        yield Label(provider, classes="datum")

                    yield Rule()

                    yield Label("First message", classes="heading")
                    if chat.create_timestamp:
                        create_timestamp = chat.create_timestamp.replace(tzinfo=timezone.utc)
                        yield Label(
                            f"{humanize.naturaltime(create_timestamp)}",
                            classes="datum",
                        )
                    else:
                        yield Label("N/A")

                    yield Rule()

                    update_time = chat.update_time.replace(tzinfo=timezone.utc)
                    yield Label("Updated at", classes="heading")
                    if update_time:
                        yield Label(
                            f"{humanize.naturaltime(chat.update_time)}",
                            classes="datum",
                        )
                    else:
                        yield Label("N/A")

                    yield Rule()

                    yield Label("Message count", classes="heading")
                    yield Label(str(len(chat.messages) - 1), classes="datum")
