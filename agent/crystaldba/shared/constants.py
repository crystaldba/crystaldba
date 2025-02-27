"""Shared constants used by both client and server components."""

import os
from typing import Dict
from typing import Final

from dotenv import load_dotenv

load_dotenv()

__all__ = [
    "API_ENDPOINTS",
    "HTTP_SIGNATURE_MAX_AGE_SECONDS",
    "MAX_PROFILE_NAME_LENGTH",
    "get_crystal_api_url",
]

# Network settings
CRYSTAL_API_URL: str = os.environ.get("CRYSTAL_API_URL", "https://api.crystaldba.net").rstrip("/")


def get_crystal_api_url():
    return CRYSTAL_API_URL


# API Endpoints
API_ENDPOINTS: Final[Dict[str, str]] = {
    "REGISTER": "/system/register",
    "REGISTER_CHAT": "/system/register/chat",
    "PREFERENCES": "/system/preferences",
    "CHAT_START": "/chat/start",
    "CHAT_CONTINUE": "/chat/{thread_id}",  # TODO - append here?
    "HEALTH": "/health",
}

# Profile settings
MAX_PROFILE_NAME_LENGTH: Final[int] = 64
HTTP_SIGNATURE_MAX_AGE_SECONDS: Final[int] = 300  # 5 minutes
