import shutil
import textwrap


def make_clickable(url):
    return f"\033]8;;{url}\033\\{url}\033]8;;\033\\"


def wrap_text_to_terminal(text: str) -> str:
    width = shutil.get_terminal_size().columns
    lines = text.splitlines()
    wrapped_lines = []
    for line in lines:
        if line.strip():
            wrapped_lines.extend(textwrap.wrap(line, width=width))
        else:
            wrapped_lines.append("")
    return "\n".join(wrapped_lines)
