import logging
import os
import signal
import sys

import pexpect
import pytest
from pexpect.popen_spawn import PopenSpawn

from crystaldba.shared.test.conftest import test_postgres_connection_string

# Prevent ruff from removing test_postgres_connection_string
_ = test_postgres_connection_string

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@pytest.mark.parametrize("test_postgres_connection_string", ["postgres:16"], indirect=True)
def test_client_server_interaction(test_postgres_connection_string):
    """
    NOTE: assumes that you have a valid 'agent/.env' file.
    E2E test that verifies server-client interaction including database queries.
    """

    connection_string, db_version = test_postgres_connection_string
    if db_version != "postgres:16":
        pytest.skip("Only Postgres 16 is included in this test")

    # Make sure the OPENAI_API_KEY environment variable is set
    if not os.getenv("OPENAI_API_KEY"):
        pytest.fail("OPENAI_API_KEY environment variable is not set")

    port = 7080

    try:
        logger.info("Starting client process...")
        api_url = f"http://localhost:{port}"
        db_version = db_version.split(":")[1]
        client = PopenSpawn(
            f"poetry run crystaldba --profile t_e2e_{os.urandom(5).hex()} --api {api_url} {connection_string}", encoding="utf-8", env=os.environ
        )  # NOTE: ignore the type error. This is the right thing to do for "env"

        # Uncomment one of the lines below to log client output to a file or stdout
        # client.logfile = open("private/test_client_log.log", "w")
        client.logfile = sys.stdout

        # Go through onboarding flow
        try:
            client.expect(r"Profile\s*(.+)\s*does\s*not\s*exist\.\s*Would\s*you\s*like\s*to\s*create\s*it\?", timeout=5)
            client.sendline("y")
            client.expect("Your email address:", timeout=5)
            logger.info("Client started successfully")
            client.sendline("test@test.com")
            client.expect("Help us", timeout=5)
            client.sendline("no")
            client.expect("help you", timeout=5)
        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            logger.error(f"Client output: {client.before}")
            logger.error(f"Client failed to start: {e!s}")
            raise

        logger.info("Initial communication start query")
        try:
            client.expect("Executing query", timeout=30)
            logger.info("Initial communication turn")
        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            logger.error(f"Client output: {client.before} :: {client.after}")
            logger.error(f"Database version query failed: {e!s}")
            print(str(client))
            raise

        # Test database version query
        logger.info("Testing database version query...")
        client.sendline("what version is my database?")
        try:
            client.expect(rf"{db_version}", timeout=30)
            logger.info("Database version query successful")
        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            logger.error(f"Client output: {client.before} :: {client.after}")
            logger.error(f"Database version query failed: {e!s}")
            print(str(client))
            raise

        # Test database name query
        logger.info("Testing database name query...")
        client.sendline("what is the name of my database?")
        try:
            client.expect(r"current_database|Your|your", timeout=25)
            logger.info("Database name query successful")
        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            logger.error(f"Client output: {client.before} :: {client.after}")
            logger.error(f"Database name query failed: {e!s}")
            raise

        # Test multi-step queries
        logger.info("Testing database pg_stat_statements...")
        client.sendline(
            "What is the query that runs most frequently? "
            "Please answer, and indicate the end of your answer with 'success' (but in full caps) if you were able to discover the answer, "
            "otherwise, end it with 'FAILURE'."
        )
        try:
            client.expect("SUCCESS", timeout=30)
        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            logger.error(f"Client output: {client.before} :: {client.after}")
            logger.error(f"Database pg_stat_statements query failed: {e!s}")
            raise

    except Exception as e:
        logger.error(f"Test failed with error: {e!s}")
        pytest.fail(f"Test failed: {e!s}")

    finally:
        logger.info("Cleaning up processes...")
        # Clean up client
        if "client" in locals():
            locals()["client"].kill(signal.SIGTERM)
            # locals()["client"].close()
            logger.info("Client process terminated")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
