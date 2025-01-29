"""Shared constants used by both client and server components."""

import os
from typing import Dict
from typing import Final

from dotenv import load_dotenv

load_dotenv()

__all__ = [
    "API_ENDPOINTS",
    "CRYSTAL_API_URL",
    "HTTP_SIGNATURE_MAX_AGE_SECONDS",
    "MAX_PROFILE_NAME_LENGTH",
]

# Network settings
CRYSTAL_API_URL: Final[str] = os.environ.get("CRYSTAL_API_URL", "https://api.crystaldba.net").rstrip("/")

# API Endpoints
API_ENDPOINTS: Final[Dict[str, str]] = {
    "REGISTER": "/system/register",
    "PREFERENCES": "/system/preferences",
    "CHAT_START": "/chat/start",
    "CHAT_CONTINUE": "/chat/{thread_id}",  # TODO - append here?
    "HEALTH": "/health",
}

# Profile settings
MAX_PROFILE_NAME_LENGTH: Final[int] = 64
HTTP_SIGNATURE_MAX_AGE_SECONDS: Final[int] = 300  # 5 minutes
