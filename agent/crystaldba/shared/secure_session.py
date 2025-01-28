import hashlib
import importlib.metadata
import platform
import sys
import time
from typing import Any
from typing import Callable
from typing import Dict
from typing import Protocol

if sys.version_info >= (3, 12):
    from typing import override
else:
    # Define a no-op decorator
    def override(method: Callable) -> Callable:
        return method


import requests
from http_message_signatures.algorithms import ECDSA_P256_SHA256  # pyright: ignore[reportPrivateImportUsage]
from requests_http_signature import HTTPSignatureAuth

from crystaldba.shared.base64id import generate_b64id
from crystaldba.shared.constants import HTTP_SIGNATURE_MAX_AGE_SECONDS

__version__ = importlib.metadata.version("crystaldba")


class ModelDumpProtocol(Protocol):
    """Protocol for objects that can be serialized via model_dump()."""

    def model_dump(self) -> Dict[str, Any]: ...


class SecureSession(requests.Session):
    def __init__(
        self,
        system_id: str,
        private_key: str,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.system_id = system_id
        self.private_key = private_key

    @override
    def prepare_request(self, request: requests.Request) -> requests.PreparedRequest:
        """Prepare a signed HTTP request.

        Args:
            request: The request to prepare
            **kwargs: Additional keyword arguments passed to Session.prepare_request

        Returns:
            A prepared request with appropriate headers and signature
        """
        current_time: int = int(time.time())
        headers = request.headers
        headers.update(
            {
                "system-id": self.system_id,
                "created": str(current_time),
                "expires": str(current_time + HTTP_SIGNATURE_MAX_AGE_SECONDS),
                "nonce": generate_b64id(),
                "User-Agent": f"crystaldba-cli/{__version__} (Python/{platform.python_version()}; {platform.system()}/{platform.release()})",
            }
        )

        covered_component_ids = ["@method", "@target-uri", "system-id", "created", "expires", "nonce"]

        if request.data:
            headers.update({"content-digest": f"sha-256={hashlib.sha256(request.data.encode()).hexdigest()}"})
            covered_component_ids.append("content-digest")

        auth = HTTPSignatureAuth(
            key=self.private_key.encode(),
            key_id=self.system_id,
            signature_algorithm=ECDSA_P256_SHA256,
            covered_component_ids=covered_component_ids,
        )
        request.auth = auth

        return super().prepare_request(request)


class SecureSessionFactory(Protocol):
    """Protocol for creating SecureSession instances."""

    def create_session(self, system_id: str, private_key: str) -> SecureSession: ...


class DefaultSecureSessionFactory:
    """Default implementation of SecureSessionFactory."""

    def create_session(self, system_id: str, private_key: str) -> SecureSession:
        return SecureSession(
            system_id=system_id,
            private_key=private_key,
        )
