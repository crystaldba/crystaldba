import pytest

from crystaldba.shared.test.utils import create_postgres_container


@pytest.fixture(scope="session", params=["postgres:15"])
def test_postgres_connection_string(request):
    """Create PostgreSQL containers for testing.
    Tests using this fixture will run once for each postgres version.
    """
    yield from create_postgres_container(request.param)
