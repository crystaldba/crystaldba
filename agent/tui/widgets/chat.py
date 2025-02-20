from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import cast

from textual import events
from textual import log
from textual import on
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label
from textual.worker import get_current_worker

from crystaldba.shared import api
from crystaldba.shared.api import StartupMessage
from tui import constants
from tui.models import ChatData
from tui.models import ChatMessage
from tui.widgets.agent_is_typing import ResponseStatus
from tui.widgets.chat_header import ChatHeader
from tui.widgets.chatbox import Chatbox
from tui.widgets.prompt_input import PromptInput

if TYPE_CHECKING:
    from litellm.types.completion import ChatCompletionAssistantMessageParam
    from litellm.types.completion import ChatCompletionUserMessageParam


class ChatPromptInput(PromptInput):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding(
            "escape",
            "app.quit",
            "Quit",
            key_display="esc",
        )
    ]


class Chat(Widget):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("shift+down", "scroll_container_down", show=False),
        Binding("shift+up", "scroll_container_up", show=False),
        Binding(
            key="G",
            action="focus_latest_message",
            description="Latest message",
            show=False,
        ),
    ]

    allow_input_submit = reactive(True)
    """Used to lock the chat input while the agent is responding."""

    def __init__(self, chat_data: ChatData) -> None:
        super().__init__()
        from tui.app import Tui

        self.chat_data = chat_data
        self.chat_turn_count = 0
        self.chat_turn = cast(Tui, self.app).chat_turn

    @dataclass
    class AgentResponseStarted(Message):
        pass

    @dataclass
    class AgentResponseComplete(Message):
        chat_id: int | None
        message: ChatMessage
        chatbox: Chatbox

    @dataclass
    class AgentResponseFailed(Message):
        """Sent when the agent fails to respond e.g. cant connect.
        Can be used to reset UI state."""

        last_message: ChatMessage

    @dataclass
    class NewUserMessage(Message):
        content: str

    def compose(self) -> ComposeResult:
        yield ResponseStatus()
        yield ChatHeader(
            chat=self.chat_data,
        )

        with VerticalScroll(id="chat-container") as vertical_scroll:
            vertical_scroll.can_focus = False

        yield ChatPromptInput(id="prompt")

    async def on_mount(self, _: events.Mount) -> None:
        """
        When the component is mounted, we need to check if there is a new chat to start
        """
        await self.load_chat(self.chat_data)

    @property
    def chat_container(self) -> VerticalScroll:
        return self.query_one("#chat-container", VerticalScroll)

    @property
    def is_empty(self) -> bool:
        """True if the conversation is empty, False otherwise."""
        return len(self.chat_data.messages) == 1  # Contains system message at first.

    def scroll_to_latest_message(self):
        container = self.chat_container
        container.refresh()
        container.scroll_end(animate=False, force=True)

    @on(AgentResponseFailed)
    def restore_state_on_agent_failure(self, event: Chat.AgentResponseFailed) -> None:
        original_prompt = event.last_message.message.get("content", "")
        if isinstance(original_prompt, str):
            self.query_one(ChatPromptInput).text = original_prompt

    async def new_user_message(self, content: str) -> None:
        log.debug(f"User message submitted in chat {self.chat_data.id!r}: {content!r}")

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        user_message: ChatCompletionUserMessageParam = {
            "content": content,
            "role": "user",
        }

        user_chat_message = ChatMessage(
            user_message,
            now_utc,
        )
        self.chat_data.messages.append(user_chat_message)
        user_message_chatbox = Chatbox(
            user_chat_message,
        )

        assert self.chat_container is not None, "Textual has mounted container at this point in the lifecycle."

        await self.chat_container.mount(user_message_chatbox)

        self.scroll_to_latest_message()
        self.post_message(self.NewUserMessage(content))

        assert self.chat_data.id is not None, "chat id must not be None"

        prompt = self.query_one(ChatPromptInput)
        prompt.submit_ready = False
        self.stream_agent_response()

    @work(thread=True, group="agent_response")
    def stream_agent_response(self) -> None:
        if self.chat_turn_count == 0:
            chat_turn_message = StartupMessage()
            self.handle_stream_agent_response(chat_turn_message)
            self.chat_turn_count = 1
            return
        messages = [self.chat_data.messages[-1]] if len(self.chat_data.messages) > 0 else []
        the_string = " ".join(extract_messages_text(item) for item in messages)
        chat_turn_message = api.ChatMessage(message=the_string)
        self.handle_stream_agent_response(chat_turn_message)

    # NOTE: must be run on a thread by the caller
    def handle_stream_agent_response(self, chat_turn_message: StartupMessage | api.ChatMessage) -> None:
        if get_current_worker().is_cancelled:
            return
        log.debug("stream_agent_response_startup")

        ai_message: ChatCompletionAssistantMessageParam = {
            "content": "",
            "role": "assistant",
        }
        now = datetime.datetime.now(datetime.timezone.utc)
        message = ChatMessage(
            message=ai_message,
            timestamp=now,
        )
        response_chatbox = Chatbox(
            message=message,
            classes="response-in-progress",
        )
        self.post_message(self.AgentResponseStarted())
        self.app.call_from_thread(self.chat_container.mount, response_chatbox)
        assert self.chat_container is not None, "Textual has mounted container at this point in the lifecycle."

        try:
            chunk_count = 0
            self.app.call_from_thread(self.chat_container.scroll_end, animate=False)
            for chunk in self.chat_turn.run_to_completion(chat_turn_message):
                response_chatbox.border_title = "Agent is responding..."

                scroll_y = self.chat_container.scroll_y
                max_scroll_y = self.chat_container.max_scroll_y
                # import logging
                # logger = logging.getLogger(__name__)
                # logger.warning(f"DEBUGSHORT log position {scroll_y} = {max_scroll_y}")
                if scroll_y in range(max_scroll_y - 5, max_scroll_y + 1):
                    self.app.call_from_thread(self.chat_container.scroll_end, animate=False)
                if chunk is None:
                    break
                if isinstance(chunk, str):
                    self.app.call_from_thread(response_chatbox.append_chunk, chunk)
                else:
                    break
                chunk_count += 1

        except Exception:
            self.notify(
                "There was a problem with the chat turn.",
                title="Error",
                severity="error",
                timeout=constants.ERROR_NOTIFY_TIMEOUT_SECS,
            )
            self.post_message(self.AgentResponseFailed(self.chat_data.messages[-1]))
        else:
            self.post_message(
                self.AgentResponseComplete(
                    chat_id=self.chat_data.id,
                    message=response_chatbox.message,
                    chatbox=response_chatbox,
                )
            )

    @on(AgentResponseFailed)
    @on(AgentResponseStarted)
    async def agent_started_responding(self, event: AgentResponseFailed | AgentResponseStarted) -> None:
        try:
            awaiting_reply = self.chat_container.query_one("#awaiting-reply", Label)
        except NoMatches:
            pass
        else:
            if awaiting_reply:
                await awaiting_reply.remove()

    @on(AgentResponseComplete)
    def agent_finished_responding(self, event: AgentResponseComplete) -> None:
        # Ensure the thread is updated with the message from the agent
        self.chat_data.messages.append(event.message)
        event.chatbox.border_title = "Agent"
        event.chatbox.remove_class("response-in-progress")
        prompt = self.query_one(ChatPromptInput)
        prompt.submit_ready = True

    @on(PromptInput.PromptSubmitted)
    async def user_chat_message_submitted(self, event: PromptInput.PromptSubmitted) -> None:
        if self.allow_input_submit is True:
            user_message = event.text
            await self.new_user_message(user_message)

    @on(PromptInput.CursorEscapingTop)
    async def on_cursor_up_from_prompt(self, event: PromptInput.CursorEscapingTop) -> None:
        self.focus_latest_message()

    @on(Chatbox.CursorEscapingBottom)
    def move_focus_to_prompt(self) -> None:
        self.query_one(ChatPromptInput).focus()

    def get_latest_chatbox(self) -> Chatbox:
        return self.query(Chatbox).last()

    def focus_latest_message(self) -> None:
        try:
            self.get_latest_chatbox().focus()
        except NoMatches:
            pass

    def action_focus_latest_message(self) -> None:
        self.focus_latest_message()

    def action_focus_first_message(self) -> None:
        try:
            self.query(Chatbox).first().focus()
        except NoMatches:
            pass

    def action_scroll_container_up(self) -> None:
        if self.chat_container:
            self.chat_container.scroll_up()

    def action_scroll_container_down(self) -> None:
        if self.chat_container:
            self.chat_container.scroll_down()

    async def load_chat(self, chat_data: ChatData) -> None:
        chatboxes = [
            Chatbox(
                chat_message,
            )
            for chat_message in chat_data.non_system_messages
        ]
        chatboxes = chatboxes[1:]  # skip the first item since it is empty
        await self.chat_container.mount_all(chatboxes)
        self.chat_container.scroll_end(animate=False, force=True)
        chat_header = self.query_one(ChatHeader)
        chat_header.update_header(
            chat=chat_data,
        )

        # If the last message didn't receive a response, try again.
        messages = chat_data.messages
        if messages and messages[-1].message["role"] == "user":
            prompt = self.query_one(ChatPromptInput)
            prompt.submit_ready = False
            self.stream_agent_response()

    def action_close(self) -> None:
        self.app.clear_notifications()
        self.app.pop_screen()


def extract_messages_text(item: ChatMessage) -> str:
    return str(item.message)


# def extract_messages_text(item: ChatCompletionUserMessageParam) -> str:
#     content = item.get("content", "")
#     # If it's a string, return it directly.
#     if isinstance(content, str):
#         return content
#     # Otherwise, assume it's an iterable of parts and join them.
#     elif isinstance(content, collections.abc.Iterable):
#         # Convert each element to a string (in case they aren't already)
#         return " ".join(str(part) for part in content)
#     else:
#         return str(content)
