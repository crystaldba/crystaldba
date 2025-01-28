from typing import Any
from typing import AsyncGenerator
from typing import Iterator
from typing import Optional
from typing import Protocol
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import JsonValue

from .base64id import Base64Id


class Registration(BaseModel):
    """Registration request model for system registration."""

    system_id: Base64Id
    public_key: str
    email: EmailStr
    agree_tos: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "system_id": "A1B2C3D4E5F6G7H8I9J0K_",
                "public_key": "-----BEGIN PUBLIC KEY-----\n...",
                "email": "user@example.com",
                "agree_tos": True,
            }
        }
    )

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Override model_dump to handle UUID serialization."""
        data = super().model_dump(**kwargs)
        data["system_id"] = str(data["system_id"])
        return data


class SystemPreferences(BaseModel):
    """Preferences request model for system preferences."""

    share_data: bool


class ChatMessage(BaseModel):
    message: str


class ChatMessageFragment(BaseModel):
    message_fragment: str


class ChatMessageDone(BaseModel):
    pass


class SQLToolExecuteRequest(BaseModel):
    query: str


class SQLToolExecuteResponse(BaseModel):
    """JSON-serializable representation of list[BaseSqlDriver.RowResult] | None"""

    rows: Optional[list[dict[str, JsonValue]]]


class SQLToolErrorResponse(BaseModel):
    error_string: str


class SQLToolSchemaRequest(BaseModel):
    table_name: str
    db_schema: Optional[str]


class SQLToolSchemaResponse(BaseModel):
    table_schema: Optional[str]


class ChatRequest(BaseModel):
    sequence_id: int
    continuation_token: Optional[str]
    payload: Union[ChatMessage, SQLToolExecuteResponse, SQLToolErrorResponse, SQLToolSchemaResponse]


class ChatResponse(BaseModel):
    sequence_id: int
    continuation_token: Optional[str]
    payload: Union[ChatMessage, ChatMessageFragment, SQLToolExecuteRequest, SQLToolSchemaRequest, ChatMessageDone]


class DbaChatSyncProtocol(Protocol):
    """Protocol defining the DbaChat interface for Server, Remote, and Client"""

    def turn(self, request: ChatRequest) -> Iterator[ChatResponse]:
        """Execute 1 turn in the conversation.

        Args:
            request: The incoming chat request

        Returns:
            A ChatResponse (sync)
        """
        ...


class DbaChatAsyncProtocol(Protocol):
    """Protocol defining the DbaChat interface for Server, Remote, and Client"""

    def turn(self, request: ChatRequest) -> AsyncGenerator[ChatResponse, None]:
        """Execute 1 turn in the conversation.

        Args:
            request: The incoming chat request

        Yields:
            ChatResponse objects as they become available
        """
        ...
