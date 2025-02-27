"""Constants specific to the Crystal DBA client."""

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()

__all__ = [
    "CRYSTAL_CONFIG_DIRECTORY",
    "DATABASE_URL",
    "DEFAULT_PROFILE_NAME",
    "MAX_PROFILE_NAME_LENGTH",
]

DATABASE_URL: Final[str | None] = os.environ.get("DATABASE_URL")

# Profile settings
DEFAULT_PROFILE_NAME: Final[str] = "default"
MAX_PROFILE_NAME_LENGTH: Final[int] = 16

# Configuration
CRYSTAL_CONFIG_DIRECTORY: Final[Path] = (
    Path(os.environ.get("CRYSTAL_CONFIG_DIR", "")) if os.environ.get("CRYSTAL_CONFIG_DIR") else Path.home() / ".crystal"
)
