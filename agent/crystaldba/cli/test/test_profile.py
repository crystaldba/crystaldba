import tempfile
from pathlib import Path

import pytest
import yaml
from pytest_mock import MockerFixture

from crystaldba.cli.profile import MAX_PROFILE_NAME_LENGTH
from crystaldba.cli.profile import ConfigUpdateError
from crystaldba.cli.profile import Profile
from crystaldba.cli.profile import ProfilesConfig
from crystaldba.cli.profile import _create_new_profile  # pyright: ignore[reportPrivateUsage]
from crystaldba.cli.profile import _update_profile  # pyright: ignore[reportPrivateUsage]
from crystaldba.shared.secure_session import SecureSession


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_session(mocker: MockerFixture):
    return mocker.Mock()


class TestProfile:
    def test_validate_profile_name_valid_cases(self):
        """Test profile name validation with valid inputs"""
        valid_names = [
            "default",
            "test_profile",
            "profile123",
            "my_profile_2",
            "_hidden",
            "a" * MAX_PROFILE_NAME_LENGTH,  # Max length
        ]
        for name in valid_names:
            assert Profile.validate_profile_name(name) is True

    def test_validate_profile_name_invalid_cases(self):
        """Test profile name validation with invalid inputs"""
        invalid_names = [
            "",  # Empty
            "a" * (MAX_PROFILE_NAME_LENGTH + 1),  # Too long
            "a" * 100,  # Too long
            "123profile",  # Starts with number
            "test@profile",  # Invalid character
            "test profile",  # Space
            "-profile",  # Starts with hyphen
            "profile!",  # Special character
            "profile/name",  # Path separator
        ]
        for name in invalid_names:
            assert Profile.validate_profile_name(name) is False

    def test_new_profile_creation(self):
        """Test creation of new profile with valid inputs"""
        name = "test_profile"
        email = "test@example.com"

        profile = Profile.new(name=name, email=email)

        assert profile.name == name
        assert profile.email == email
        assert isinstance(str(profile.system_id), str)
        assert isinstance(profile.public_key, str)
        assert isinstance(profile.private_key, str)
        assert profile.share_data is False

    def test_new_profile_invalid_name(self):
        """Test profile creation with invalid name raises ValueError"""
        with pytest.raises(ValueError, match="Invalid profile name"):
            Profile.new(name="invalid@name", email="test@example.com")

    def test_profile_to_dict(self):
        """Test profile serialization to dict"""
        profile = Profile(name="test", system_id="abc123", email="test@example.com", share_data=True, public_key="pub_key", private_key="priv_key")

        result = profile.to_dict()

        assert result == {"system_id": "abc123", "email": "test@example.com", "share_data": True}


class TestProfilesConfig:
    def test_create_profile(self, temp_dir):
        """Test creating a new profile in the config"""
        config = ProfilesConfig(config_dir=temp_dir)
        profile = Profile(name="test", system_id="abc123", email="test@example.com", share_data=False, public_key="pub_key", private_key="priv_key")

        config.create_profile(profile)

        # Verify files were created
        profile_dir = temp_dir / str(profile.system_id)
        assert profile_dir.exists()
        assert (profile_dir / "private_key.pem").exists()
        assert (profile_dir / "public_key.pem").exists()

        # Verify config file content
        with open(temp_dir / "config.yaml") as f:
            saved_config = yaml.safe_load(f)
            assert saved_config["test"] == profile.to_dict()

    def test_get_profile(self, temp_dir):
        """Test retrieving a profile from config"""
        profile_data = {"test": {"system_id": "abc123", "email": "test@example.com", "share_data": False}}

        # Setup test config and key files
        profile_dir = temp_dir / "abc123"
        profile_dir.mkdir(parents=True)
        with open(temp_dir / "config.yaml", "w") as f:
            yaml.dump(profile_data, f)
        with open(profile_dir / "private_key.pem", "w") as f:
            f.write("priv_key")
        with open(profile_dir / "public_key.pem", "w") as f:
            f.write("pub_key")

        config = ProfilesConfig(config_dir=temp_dir)
        profile = config.get_profile("test")

        assert profile is not None
        assert profile.name == "test"
        assert str(profile.system_id) == "abc123"
        assert profile.email == "test@example.com"
        assert profile.share_data is False
        assert profile.private_key == "priv_key"
        assert profile.public_key == "pub_key"

    def test_edit_profile(self, temp_dir):
        """Test editing an existing profile"""
        config = ProfilesConfig(config_dir=temp_dir)
        initial_profile = Profile(
            name="test", system_id="abc123", email="test@example.com", share_data=False, public_key="pub_key", private_key="priv_key"
        )
        config.create_profile(initial_profile)

        def update_fn(p: Profile):
            p.share_data = True
            p.email = "new@example.com"

        config.edit_profile("test", update_fn)

        updated_profile = config.get_profile("test")
        assert updated_profile is not None
        assert updated_profile.share_data is True
        assert updated_profile.email == "new@example.com"


class TestNewProfile:
    @pytest.mark.private
    def test_create_new_profile(self, temp_dir, mock_session, mocker: MockerFixture):
        """Test the full profile creation workflow"""
        config = ProfilesConfig(config_dir=temp_dir)

        def mock_get_email(_):
            return "test@example.com"

        def mock_get_share_data():
            return True

        class TestSecureSessionFactory:
            def create_session(self, system_id: str, private_key: str) -> SecureSession:
                return mock_session

        mock_prepared_request = mocker.Mock()
        mock_session.prepare_request.return_value = mock_prepared_request
        mock_response = mocker.Mock()
        mock_response.raise_for_status.return_value = None
        mock_session.send.return_value = mock_response
        profile, _ = _create_new_profile(
            "test_profile",
            config,
            ui_get_email_function=mock_get_email,
            ui_get_share_data_function=mock_get_share_data,
            session_factory=TestSecureSessionFactory(),
        )

        assert profile.name == "test_profile"
        assert profile.email == "test@example.com"
        assert profile.share_data is True
        mock_session.prepare_request.assert_called()
        mock_session.send.assert_called_with(mock_prepared_request)  # Verify HTTP request was made
        assert mock_session.send.call_count == 2  # verify both registration and preferences call


class TestProfileUpdate:
    @pytest.mark.private
    def test_update_profile_concurrent_modification(self, temp_dir):
        """Test handling of concurrent profile updates"""
        config_file = temp_dir / "config.yaml"
        profile = Profile(name="test", system_id="abc123", email="test@example.com", share_data=False, public_key="pub_key", private_key="priv_key")

        # Create initial config
        with open(config_file, "w") as f:
            yaml.dump({"test": profile.to_dict()}, f)

        # Simulate unexpected concurrent modification
        profile.email = "unexpected-change-since-config-was-written-to-disk@example.com"

        # New version that won't get written because of unexpected concurrent modification
        modified_profile = Profile(
            name="test", system_id="xyz789", email="other@example.com", share_data=True, public_key="pub_key2", private_key="priv_key2"
        )

        with pytest.raises(ConfigUpdateError):
            _update_profile(config_file, "test", profile, modified_profile)
