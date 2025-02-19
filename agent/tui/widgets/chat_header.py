from __future__ import annotations

from dataclasses import dataclass

from rich.console import ConsoleRenderable
from rich.console import RichCast
from rich.markup import escape
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from tui.models import ChatData


class TitleStatic(Static):
    @dataclass
    class ChatRenamed(Message):
        chat_id: int
        new_title: str

    def __init__(
        self,
        chat_id: int | None,
        renderable: ConsoleRenderable | RichCast | str = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            renderable,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.chat_id = chat_id


class ChatHeader(Widget):
    def __init__(
        self,
        chat: ChatData,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.chat = chat

    def update_header(
        self,
        chat: ChatData,
    ):
        self.chat = chat

        title_static = self.query_one("#title-static", Static)

        title_static.update(self.title_static_content())

    def title_static_content(self) -> str:
        chat = self.chat
        content = escape(chat.title or chat.short_preview or "") if chat else "Empty chat"
        return f"{content}"

    def compose(self) -> ComposeResult:
        yield TitleStatic(self.chat.id, self.title_static_content(), id="title-static")
