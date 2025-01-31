import fcntl
import json
import logging
import os
import string
import sys
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple

import requests
import yaml
from email_validator import EmailNotValidError
from email_validator import validate_email
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm

from crystaldba.cli.constants import CRYSTAL_CONFIG_DIRECTORY
from crystaldba.cli.constants import MAX_PROFILE_NAME_LENGTH
from crystaldba.cli.keypair import generate_keypair
from crystaldba.cli.ui import make_clickable
from crystaldba.cli.ui import wrap_text_to_terminal
from crystaldba.shared.api import Registration
from crystaldba.shared.api import SystemPreferences
from crystaldba.shared.base64id import Base64Id
from crystaldba.shared.base64id import generate_b64id
from crystaldba.shared.constants import API_ENDPOINTS
from crystaldba.shared.constants import CRYSTAL_API_URL
from crystaldba.shared.secure_session import DefaultSecureSessionFactory
from crystaldba.shared.secure_session import SecureSession
from crystaldba.shared.secure_session import SecureSessionFactory

VALID_PROFILE_CHARS = set(string.ascii_letters + string.digits + "_-")


@dataclass
class Profile:
    name: str
    system_id: Base64Id
    email: str
    share_data: bool
    public_key: str
    private_key: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "email": self.email,
            "share_data": self.share_data,
        }

    @property
    def config_dir(self) -> Path:
        return CRYSTAL_CONFIG_DIRECTORY / self.system_id

    @classmethod
    def new(cls, name: str, email: str) -> "Profile":
        if not cls.validate_profile_name(name):
            raise ValueError(f"Invalid profile name: {name}")

        system_id = generate_b64id()

        private_key, public_key = generate_keypair()
        return cls(name=name, email=email, system_id=system_id, share_data=False, public_key=public_key, private_key=private_key)

    @classmethod
    def validate_profile_name(cls, name: str) -> bool:
        """Validate profile name for use as a directory name."""
        if not name:
            return False
        return bool(
            name and len(name) <= MAX_PROFILE_NAME_LENGTH and (name[0].isalpha() or name[0] == "_") and all(c in VALID_PROFILE_CHARS for c in name)
        )


def get_or_create_profile(
    profile_name: str,
) -> Tuple[Profile, SecureSession]:
    profiles_config = ProfilesConfig()
    profile = profiles_config.get_profile(profile_name)
    if profile:
        logger = logging.getLogger(__name__)
        logger.info(f"Loaded profile: {profile_name}. System ID: {profile.system_id}")
        return profile, SecureSession(
            system_id=profile.system_id,
            private_key=profile.private_key,
        )

    return _create_new_profile(profile_name, profiles_config)


class ProfilesConfig:
    """Configuration for the CrystalDBA Agent."""

    config_dir: Path
    profiles: Dict[str, Profile]

    def __init__(self, config_dir: Path = CRYSTAL_CONFIG_DIRECTORY):
        self.config_dir = config_dir
        self.profiles = self._load_profiles()

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.yaml"

    def get_profile(self, profile_name: str) -> Optional[Profile]:
        return self.profiles.get(profile_name)

    def create_profile(self, profile: Profile) -> None:
        # Create profile directory and save keys
        profile_dir = self.config_dir / str(profile.system_id)
        profile_dir.mkdir(parents=True, exist_ok=True)

        private_key_path = profile_dir / "private_key.pem"
        public_key_path = profile_dir / "public_key.pem"

        private_key_path.touch(mode=0o600, exist_ok=False)
        with private_key_path.open("w") as f:
            f.write(profile.private_key)
        os.chmod(private_key_path, 0o400)

        public_key_path.touch(mode=0o644, exist_ok=False)
        with public_key_path.open("w") as f:
            f.write(profile.public_key)
        os.chmod(public_key_path, 0o444)

        self.config_dir.mkdir(parents=True, exist_ok=True)
        _update_profile(self.config_file, profile.name, None, profile)
        # reload profiles
        self.profiles = self._load_profiles()

    def edit_profile(self, profile_name: str, edit_fn: Callable[[Profile], None]) -> None:
        prev_profile = self.get_profile(profile_name)
        if prev_profile is None:
            raise ValueError(f"Profile '{profile_name}' not found")
        new_profile = replace(prev_profile)  # This duplicates the profile object
        edit_fn(new_profile)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        _update_profile(self.config_file, profile_name, prev_profile, new_profile)
        # reload profiles
        self.profiles = self._load_profiles()

    def _load_profiles(self) -> Dict[str, Profile]:
        config_file = self.config_dir / "config.yaml"
        if not config_file.exists():
            return {}

        with open(config_file) as f:
            yaml_data = yaml.safe_load(f)
            if not yaml_data:
                return {}
            profiles = {}
            for name, profile_data in yaml_data.items():
                try:
                    profile_dir = self.config_dir / str(profile_data["system_id"])
                    private_key_path = profile_dir / "private_key.pem"
                    public_key_path = profile_dir / "public_key.pem"

                    with private_key_path.open("r") as f:
                        private_key = f.read()
                    with public_key_path.open("r") as f:
                        public_key = f.read()

                    profiles[name] = Profile(
                        name=name,
                        system_id=profile_data["system_id"],
                        email=profile_data["email"],
                        share_data=profile_data.get("share_data", False),
                        private_key=private_key,
                        public_key=public_key,
                    )
                except (KeyError, FileNotFoundError, ValueError) as e:
                    logging.warning(f"Failed to load profile {name}: {e}")
                    continue
            return profiles


def _update_profile(config_file: Path, profile_name: str, prev_profile: Optional[Profile], new_profile: Profile) -> None:
    """Atomically update config file if the profile hasn't changed since reading.
    Raises ConfigUpdateError if there was a concurrent modification.
    """

    # We use a+ to create the file if it doesn't exist
    with open(config_file, "a+") as f:
        # Get exclusive lock
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            # Read current config
            f.seek(0)
            current_config = yaml.safe_load(f) or {}

            # Check if profile changed since we read it
            if profile_name in current_config:
                if prev_profile is not None and current_config[profile_name] != prev_profile.to_dict():
                    raise ConfigUpdateError(f"Profile '{profile_name}' was modified by another process")

            new_config = current_config.copy()
            new_config[profile_name] = new_profile.to_dict()

            # Write new config to temp file
            temp_file = config_file.with_suffix(".tmp")
            with open(temp_file, "w") as tmp:
                yaml.dump(new_config, tmp)

            # Atomic rename
            temp_file.rename(config_file)

        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _ui_get_email(
    profile_name: str,
) -> str:
    logger = logging.getLogger(__name__)

    if profile_name != "default":
        print()
        try:
            if not confirm(wrap_text_to_terminal(f"Profile '{profile_name}' does not exist. Would you like to create it?"), suffix=" (y/N): "):
                print("Exiting.")
                sys.exit(0)
        except KeyboardInterrupt:
            sys.exit(1)
        print(wrap_text_to_terminal(f"Creating profile: {profile_name}"))

    if not Profile.validate_profile_name(profile_name):
        logger.critical("Invalid profile name")
        print(
            wrap_text_to_terminal(
                f"Error: Profile name must be 1-{MAX_PROFILE_NAME_LENGTH} characters long and contain "
                "only letters, numbers, underscore, or hyphen. Must start with a letter or underscore.",
            )
        )
        sys.exit(1)

    tos_message = (
        "Please enter your email address to register this system. By entering your "
        "email address, you acknowledge that you have read, understood, and agree to "
        "be bound by the Crystal Customer Terms and Conditions (as made available "
        "from time to time at " + make_clickable("https://www.crystaldba.ai/customer-terms-and-conditions") + ")."
    )
    print()
    print(wrap_text_to_terminal(tos_message))
    while True:
        email = prompt("\nYour email address: ").strip()

        try:
            validate_email(email)
            break
        except EmailNotValidError as e:
            print(f"Invalid email address: {e!s}")
            print("Please try again.")

    print()
    print(wrap_text_to_terminal("Registering system with server..."))

    return email


def _ui_get_share_data() -> bool:
    # Ask if they want to share usage data
    share_data_str: str
    while True:
        usage_data_prompt = (
            "Would you like to share Usage Data with us to improve our products "
            "and services? If you answer 'No', we will not use such Usage Data "
            "for such purposes notwithstanding anything to the contrary in the "
            "Crystal Customer Terms and Conditions (as made available from time "
            "to time at " + make_clickable("https://www.crystaldba.ai/customer-terms-and-conditions") + ")."
        )
        print()
        print(wrap_text_to_terminal(usage_data_prompt))
        share_data_str = prompt("\nHelp us? (yes/no) ").lower().strip()
        if share_data_str in ["yes", "no"]:
            break
        print(wrap_text_to_terminal("Please enter either 'yes' or 'no'"))

    share_data = share_data_str == "yes"
    if share_data:
        print()
        print(wrap_text_to_terminal("Thank you for contributing to making Crystal DBA better!"))
    else:
        print()
        print(wrap_text_to_terminal("Your usage data will not be retained or used to improve Crystal DBA."))

    return share_data


def _create_new_profile(
    profile_name: str,
    config: ProfilesConfig,
    ui_get_email_function: Callable[[str], str] = _ui_get_email,
    ui_get_share_data_function: Callable[[], bool] = _ui_get_share_data,
    session_factory: SecureSessionFactory = DefaultSecureSessionFactory(),  # noqa: B008
) -> Tuple[Profile, SecureSession]:
    logger = logging.getLogger(__name__)
    email = ui_get_email_function(profile_name)

    profile = Profile.new(name=profile_name, email=email)

    registration = Registration(
        system_id=profile.system_id,
        public_key=profile.public_key,
        email=email,
        agree_tos=True,
    )

    session = session_factory.create_session(
        system_id=profile.system_id,
        private_key=profile.private_key,
    )

    try:
        prepared_request = session.prepare_request(
            requests.Request(
                method="POST",
                url=f"{CRYSTAL_API_URL}{API_ENDPOINTS['REGISTER']}",
                data=json.dumps(registration.model_dump()),
            )
        )

        response = session.send(prepared_request)
        response.raise_for_status()
    except requests.HTTPError as e:
        logger.critical(f"Error registering with server: {e!r}")
        print(wrap_text_to_terminal(f"Error registering with server: {e!s}"))
        sys.exit(1)

    try:
        config.create_profile(profile)
    except ConfigUpdateError as e:
        logger.critical(f"Error registering with server: {e!r}")
        print(f"Error creating the profile: {e!s}")
        sys.exit(1)

    share_data = ui_get_share_data_function()

    if share_data:
        try:
            prepared_request = session.prepare_request(
                requests.Request(
                    method="POST",
                    url=f"{CRYSTAL_API_URL}{API_ENDPOINTS['PREFERENCES']}",
                    data=json.dumps(SystemPreferences(share_data=True).model_dump()),
                )
            )
            response = session.send(prepared_request)
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.critical(f"Error updating preferences: {e!r}")
            print(f"Error updating preferences: {e!s}")
            sys.exit(1)
        try:

            def update_fn(p: Profile) -> None:
                p.share_data = True

            config.edit_profile(profile.name, update_fn)
            profile = config.get_profile(profile_name)
            if profile is None:
                raise ConfigUpdateError("Profile not found after update")
        except ConfigUpdateError as e:
            logger.critical(f"Error for config update: {e!r}")
            print(f"Error for config update: {e!s}")
            sys.exit(1)
        logger.info("share_data: True")
    else:
        profile.share_data = False
        logger.info("share_data: False")

    return profile, session


class ConfigUpdateError(Exception):
    """Raised when there is an error updating the config file."""

    pass
