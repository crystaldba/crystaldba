from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litellm.types.completion import ChatCompletionMessageParam


@dataclass
class ChatMessage:
    message: ChatCompletionMessageParam
    timestamp: datetime | None


@dataclass
class ChatData:
    id: int | None  # Can be None before the chat gets assigned ID from database.
    title: str | None
    create_timestamp: datetime | None
    messages: list[ChatMessage]

    @property
    def short_preview(self) -> str | None:
        if not self.messages:
            return None
        first_message = self.first_user_message.message

        if "content" in first_message:
            first_message = first_message["content"]
            # We have content, but it's not guaranteed to be a string quite yet.
            # In the case of tool calls or image generation requests, we can
            # have non-string types here. We're not handling/considering this atm.
            if first_message and isinstance(first_message, str):
                if len(first_message) > 77:
                    return first_message[:77] + "..."
                else:
                    return first_message

        return ""

    @property
    def system_prompt(self) -> ChatMessage:
        return self.messages[0]

    @property
    def first_user_message(self) -> ChatMessage:
        return self.messages[1]

    @property
    def non_system_messages(
        self,
    ) -> list[ChatMessage]:
        return self.messages[1:]

    @property
    def update_time(self) -> datetime:
        message_timestamp = self.messages[-1].timestamp
        if message_timestamp is None:
            return datetime.now(UTC)
        return message_timestamp.astimezone().replace(tzinfo=UTC)
