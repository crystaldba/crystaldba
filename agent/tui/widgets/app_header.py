from importlib.metadata import version
from typing import ClassVar
from typing import cast

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label

from tui.app import Tui

TUI_VERSION = version("crystaldba")


class AppHeader(Widget):
    COMPONENT_CLASSES: ClassVar[set[str]] = {"app-title", "app-subtitle"}

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.tui = cast(Tui, self.app)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="cl-header-container"):
                yield Label(
                    Text("TUI") + Text(f" v{TUI_VERSION}", style="dim"),
                    id="tui-title",
                )
