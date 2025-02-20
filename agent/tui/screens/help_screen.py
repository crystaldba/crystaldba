from typing import ClassVar
from typing import List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer
from textual.widgets import Markdown


class HelpScreen(ModalScreen[None]):
    BINDINGS: ClassVar[List[Binding]] = [
        Binding("q", "app.quit", "Quit", show=False),
        Binding("escape,f1,?", "app.pop_screen()", "Close help", key_display="esc"),
    ]

    HELP_MARKDOWN = """\
### How do I quit this app?

Press `Ctrl+C` on your keyboard.
`Ctrl+q` also works to quit.

### General navigation

This app has very strong mouse support. Most things can be clicked.

Use `tab` and `shift+tab` to move between different widgets on screen.

In some places you can make use of the arrow keys or Vim nav keys to move around.

In general, pressing `esc` will move you "closer to exiting".
Pay attention to the bar at the bottom to see where `esc` will take you.

If you can see a scrollbar, `pageup`, `pagedown`, `home`, and `end` can also
be used to navigate.

On the chat screen, pressing `up` and `down` will navigate through messages,
but if you just wish to scroll a little, you can use `shift+up` and `shift+down`.

### Writing a prompt

The shortcuts below work when the _prompt editor_ is focused.
The prompt editor is the box where you type your message.

- `enter`: Submit the prompt
- `ctrl+j`: Add a new line to the prompt
- `alt+enter`: Add a new line to the prompt (only works in some terminals)
- `up`: Move the cursor up
- `down`: Move the cursor down
- `left`: Move the cursor left
- `ctrl+left`: Move the cursor to the start of the word
- `ctrl+shift+left`: Move the cursor to the start of the word and select
- `right`: Move the cursor right
- `ctrl+right`: Move the cursor to the end of the word
- `ctrl+shift+right`: Move the cursor to the end of the word and select
- `home,ctrl+a`: Move the cursor to the start of the line
- `end,ctrl+e`: Move the cursor to the end of the line
- `shift+home`: Move the cursor to the start of the line and select
- `shift+end`: Move the cursor to the end of the line and select
- `pageup`: Move the cursor one page up
- `pagedown`: Move the cursor one page down
- `shift+up`: Select while moving the cursor up
- `shift+down`: Select while moving the cursor down
- `shift+left`: Select while moving the cursor left
- `backspace`: Delete character to the left of cursor
- `ctrl+w`: Delete from cursor to start of the word
- `delete,ctrl+d`: Delete character to the right of cursor
- `ctrl+f`: Delete from cursor to end of the word
- `ctrl+x`: Delete the current line
- `ctrl+u`: Delete from cursor to the start of the line
- `ctrl+k`: Delete from cursor to the end of the line
- `f6`: Select the current line
- `f7`: Select all text in the document
- `ctrl+z`: Undo last edit
- `ctrl+y`: Redo last undo
- `cmd+v` (mac): Paste
- `ctrl+v` (windows/linux): Paste

You can also click to move the cursor, and click and drag to select text.

The arrow keys can also be used to move focus _out_ of the prompt box.
For example, pressing `up` while the prompt is focussed on the chat screen
and the cursor is at (0, 0) will move focus to the latest message.

### The chat screen

You can use the arrow keys to move up and down through messages.

_With a message focused_:

- `y,c`: Copy the raw Markdown of the message to the clipboard.
    - This requires terminal support. The default MacOS terminal is not supported.
- `enter`: Enter _select mode_.
    - In this mode, you can move a cursor through the text, optionally holding
        `shift` to select text as you move.
    - Press `v` to toggle _visual mode_, allowing you to select without text without
        needing to hold `shift`.
    - Press `u` to quickly select the next code block in the message.
    - With some text selected, press `y` or c` to copy.
- `G`: Focus the latest message.
- `m`: Move focus to the prompt box.
- `up,down,k,j`: Navigate through messages.

"""

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container") as vertical:
            vertical.border_title = "App Help"
            with VerticalScroll():
                yield Markdown(self.HELP_MARKDOWN, id="help-markdown")
            yield Markdown(
                "Use `pageup`, `pagedown`, `up`, and `down` to scroll.",
                id="help-scroll-keys-info",
            )
        yield Footer()
