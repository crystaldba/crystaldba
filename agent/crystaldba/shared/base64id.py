import base64
import re
import secrets

from pydantic import AfterValidator
from typing_extensions import Annotated

EXPECTED_LENGTH = 22


def check_b64_id(value: str) -> str:
    assert len(value) == EXPECTED_LENGTH, f"Base64Id must be exactly {EXPECTED_LENGTH} characters"
    if len(value) != EXPECTED_LENGTH:
        raise ValueError("Base64Id must be exactly 22 characters")

    # Check for valid base64url characters
    if not re.match(r"^[A-Za-z0-9_-]*$", value):
        raise ValueError("Invalid characters in base64url string")
    return value


def generate_b64id() -> "Base64Id":
    """Generate a new random Base64Id."""
    random_bytes = secrets.token_bytes(16)
    # We know we'll always need to remove exactly 2 padding chars
    return base64.urlsafe_b64encode(random_bytes).decode("ascii")[:-2]


Base64Id = Annotated[str, AfterValidator(check_b64_id)]
