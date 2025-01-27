from ..api import ChatMessage
from ..api import ChatRequest
from ..api import ChatResponse
from ..api import SQLToolExecuteRequest
from ..api import SQLToolExecuteResponse
from ..api import SQLToolSchemaRequest
from ..api import SQLToolSchemaResponse


def test_chat_request_message_serialization():
    # Create a ChatRequest with ChatMessage
    request = ChatRequest(sequence_id=1, continuation_token=None, payload=ChatMessage(message="Hello, how are you?"))

    # Serialize to JSON
    json_str = request.model_dump_json()

    # Deserialize from JSON
    recovered = ChatRequest.model_validate_json(json_str)

    # Verify the objects match
    assert recovered.sequence_id == request.sequence_id
    assert recovered.continuation_token == request.continuation_token
    assert isinstance(recovered.payload, ChatMessage)
    assert recovered.payload.message == "Hello, how are you?"


def test_chat_request_sql_execute_serialization():
    # Create a ChatRequest with SQLToolExecuteResponse
    request = ChatRequest(
        sequence_id=2,
        continuation_token="token123",
        payload=SQLToolExecuteResponse(rows=[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]),
    )

    # Serialize to JSON
    json_str = request.model_dump_json()

    # Deserialize from JSON
    recovered = ChatRequest.model_validate_json(json_str)

    # Verify the objects match
    assert recovered.sequence_id == request.sequence_id
    assert recovered.continuation_token == "token123"
    assert isinstance(recovered.payload, SQLToolExecuteResponse)
    assert recovered.payload.rows is not None
    assert recovered.payload.rows[0]["name"] == "John"
    assert recovered.payload.rows[1]["name"] == "Jane"


def test_chat_request_sql_execute_serialization_empty():
    # Create a ChatRequest with SQLToolExecuteResponse with no rows
    request = ChatRequest(
        sequence_id=2,
        continuation_token="token123",
        payload=SQLToolExecuteResponse(rows=None),
    )

    # Serialize to JSON
    json_str = request.model_dump_json()

    # Deserialize from JSON
    recovered = ChatRequest.model_validate_json(json_str)

    # Verify the objects match
    assert recovered.sequence_id == request.sequence_id
    assert recovered.continuation_token == "token123"
    assert isinstance(recovered.payload, SQLToolExecuteResponse)
    assert recovered.payload.rows is None


def test_chat_response_message_serialization():
    # Create a ChatResponse with ChatMessage
    response = ChatResponse(
        sequence_id=1,
        continuation_token=None,
        payload=ChatMessage(message="I'm doing well, thanks!"),
    )

    # Serialize to JSON
    json_str = response.model_dump_json()

    # Deserialize from JSON
    recovered = ChatResponse.model_validate_json(json_str)

    # Verify the objects match
    assert recovered.sequence_id == response.sequence_id
    assert recovered.continuation_token == response.continuation_token
    assert isinstance(recovered.payload, ChatMessage)
    assert recovered.payload.message == "I'm doing well, thanks!"


def test_chat_response_sql_execute_serialization():
    # Create a ChatResponse with SQLToolExecuteRequest
    response = ChatResponse(
        sequence_id=2,
        continuation_token="token123",
        payload=SQLToolExecuteRequest(query="SELECT * FROM users"),
    )

    # Serialize to JSON
    json_str = response.model_dump_json()

    # Deserialize from JSON
    recovered = ChatResponse.model_validate_json(json_str)

    # Verify the objects match
    assert recovered.sequence_id == response.sequence_id
    assert recovered.continuation_token == "token123"
    assert isinstance(recovered.payload, SQLToolExecuteRequest)
    assert recovered.payload.query == "SELECT * FROM users"


def test_chat_request_sql_schema_serialization():
    # Create a ChatRequest with SQLToolSchemaResponse
    request = ChatRequest(
        sequence_id=3,
        continuation_token=None,
        payload=SQLToolSchemaResponse(table_schema="CREATE TABLE users (id INT, name TEXT)"),
    )

    # Serialize to JSON
    json_str = request.model_dump_json()

    # Deserialize from JSON
    recovered = ChatRequest.model_validate_json(json_str)

    # Verify the objects match
    assert recovered.sequence_id == request.sequence_id
    assert recovered.continuation_token == request.continuation_token
    assert isinstance(recovered.payload, SQLToolSchemaResponse)
    assert recovered.payload.table_schema == "CREATE TABLE users (id INT, name TEXT)"


def test_chat_response_sql_schema_serialization():
    # Create a ChatResponse with SQLToolSchemaRequest
    response = ChatResponse(
        sequence_id=3,
        continuation_token=None,
        payload=SQLToolSchemaRequest(table_name="users", db_schema="public"),
    )

    # Serialize to JSON
    json_str = response.model_dump_json()

    # Deserialize from JSON
    recovered = ChatResponse.model_validate_json(json_str)

    # Verify the objects match
    assert recovered.sequence_id == response.sequence_id
    assert recovered.continuation_token == response.continuation_token
    assert isinstance(recovered.payload, SQLToolSchemaRequest)
    assert recovered.payload.table_name == "users"
    assert recovered.payload.db_schema == "public"
