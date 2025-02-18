from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from typing import ClassVar
from typing import cast

from rich.markup import escape
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.containers import Vertical
from textual.signal import Signal
from textual.widget import Widget
from textual.widgets import Label

from tui.app import Elia
from tui.config import EliaChatModel
from tui.models import get_model
from tui.runtime_config import RuntimeConfig

try:
    ELIA_VERSION = version("crystaldba")
except PackageNotFoundError:
    ELIA_VERSION = "0.9.0rc1"  # Match pyproject.toml version


class AppHeader(Widget):
    COMPONENT_CLASSES: ClassVar[set[str]] = {"app-title", "app-subtitle"}

    def __init__(
        self,
        config_signal: Signal[RuntimeConfig],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.config_signal: Signal[RuntimeConfig] = config_signal
        self.elia = cast(Elia, self.app)

    def on_mount(self) -> None:
        def on_config_change(config: RuntimeConfig) -> None:
            self._update_selected_model(config.selected_model)

        self.config_signal.subscribe(self, on_config_change)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="cl-header-container"):
                yield Label(
                    Text("Elia") + Text(f" v{ELIA_VERSION}", style="dim"),
                    id="elia-title",
                )
            model_name_or_id = self.elia.runtime_config.selected_model.id or self.elia.runtime_config.selected_model.name
            model = get_model(model_name_or_id, self.elia.launch_config)
            yield Label(self._get_selected_model_link_text(model), id="model-label")

    def _get_selected_model_link_text(self, model: EliaChatModel) -> str:
        return f"[@click=screen.options]{escape(model.display_name or model.name)}[/]"

    def _update_selected_model(self, model: EliaChatModel) -> None:
        print(self.elia.runtime_config)
        model_label = self.query_one("#model-label", Label)
        model_label.update(self._get_selected_model_link_text(model))
