import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pytest_mock import MockerFixture

from crystaldba.shared.constants import HTTP_SIGNATURE_MAX_AGE_SECONDS
from crystaldba.shared.secure_session import DefaultSecureSessionFactory
from crystaldba.shared.secure_session import SecureSession


@pytest.fixture
def test_private_key() -> str:
    """Generate a test ECDSA private key."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()
    )
    return pem.decode("utf-8")


class TestSecureSession:
    def test_prepare_request_adds_required_headers(self, mocker: MockerFixture, test_private_key):
        """Test that prepare_request adds all required headers"""
        # Arrange
        current_time = 1234567890
        mocker.patch("time.time", return_value=current_time)
        mocker.patch("crystaldba.shared.secure_session.generate_b64id", return_value="test_nonce")
        session = SecureSession(system_id="test_system", private_key=test_private_key)

        request = requests.Request("GET", "https://api.example.com/test")

        # Act
        prepared_request = session.prepare_request(request)

        # Assert
        assert prepared_request.headers["system-id"] == "test_system"
        assert prepared_request.headers["created"] == str(current_time)
        assert prepared_request.headers["expires"] == str(current_time + HTTP_SIGNATURE_MAX_AGE_SECONDS)
        assert prepared_request.headers["nonce"] == "test_nonce"
        assert "crystaldba-cli/" in prepared_request.headers["User-Agent"]
        assert "Python/" in prepared_request.headers["User-Agent"]

    def test_prepare_request_with_body_includes_digest(self, mocker: MockerFixture, test_private_key):
        """Test that requests with bodies include content digest header"""
        session = SecureSession(system_id="test_system", private_key=test_private_key)
        request = requests.Request(
            "POST",
            "https://api.example.com/test",
            data='{"test": "data"}',
        )

        prepared_request = session.prepare_request(request)

        assert "content-digest" in prepared_request.headers
        assert prepared_request.headers["content-digest"].startswith("sha-256=")

    def test_prepare_request_signs_request(self, mocker: MockerFixture, test_private_key):
        """Test that requests are signed with appropriate components"""
        session = SecureSession(system_id="test_system", private_key=test_private_key)
        request = requests.Request("GET", "https://api.example.com/test")

        prepared_request = session.prepare_request(request)

        assert "Signature" in prepared_request.headers

    def test_secure_session_factory(self):
        """Test that factory creates session with correct parameters"""
        factory = DefaultSecureSessionFactory()

        session = factory.create_session("test_system", "test_key")

        assert isinstance(session, SecureSession)
        assert session.system_id == "test_system"
        assert session.private_key == "test_key"
