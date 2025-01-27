import base64

import pytest
from pydantic import BaseModel

from ..base64id import EXPECTED_LENGTH
from ..base64id import Base64Id
from ..base64id import generate_b64id


class Base64Test(BaseModel):
    id: Base64Id


def test_base64id_valid_creation():
    # Test valid Base64Id creation
    valid_id = "A1B2C3D4E5F6G7H8I9J0K_"
    t = Base64Test(id=valid_id)
    assert str(t.id) == valid_id


def test_base64id_generation():
    # Test generation of new Base64Id
    t = Base64Test(id=generate_b64id())
    assert len(t.id) == EXPECTED_LENGTH


def test_base64id_invalid_length():
    # Test invalid length
    with pytest.raises(ValueError, match="Base64Id must be exactly 22 characters"):
        Base64Test(id="tooshort")
    with pytest.raises(ValueError, match="Base64Id must be exactly 22 characters"):
        Base64Test(id="toolonggggggggggggggggggggg")


def test_base64id_invalid_characters():
    # Test invalid characters
    with pytest.raises(ValueError, match="Invalid characters in base64url string"):
        Base64Test(id="A1B2C3D4E5F6G7H8I9J0K!")  # ! is not valid
    with pytest.raises(ValueError, match="Invalid characters in base64url string"):
        Base64Test(id="A1B2C3D4E5F6G7H8I9J0K=")  # = is not valid


def test_base64id_uniqueness():
    # Test that generated IDs are unique
    ids = {generate_b64id() for _ in range(1000)}
    assert len(ids) == 1000  # All should be unique


def test_base64id_serialization():
    # Test string serialization
    id_str = "A1B2C3D4E5F6G7H8I9J0K_"
    t = Base64Test(id=id_str)
    assert str(t.id) == id_str
    assert repr(t.id) == f"'{id_str}'"


def test_base64id_comparison():
    # Test comparison operations
    id1: Base64Id = "A1B2C3D4E5F6G7H8I9J0K_"
    id2: Base64Id = "A1B2C3D4E5F6G7H8I9J0K_"
    id3: Base64Id = "B1B2C3D4E5F6G7H8I9J0K_"

    assert id1 == id2
    assert id1 != id3
    assert id1 < id3
    assert id3 > id1


def test_base64id_invalid_type():
    # Test invalid input type
    with pytest.raises(ValueError):
        Base64Test(id=123)  # type: ignore
    with pytest.raises(ValueError):
        Base64Test(id=None)  # type: ignore


def test_base64id_decode():
    # Test that the ID can be properly decoded
    valid_id = "A1B2C3D4E5F6G7H8I9J0K_"
    t = Base64Test(id=valid_id)
    # Add padding and decode
    decoded = base64.urlsafe_b64decode(str(t.id) + "==")
    assert len(decoded) == 16  # Should decode to exactly 16 bytes
