# CrystalDBA Agent

## Prerequisites

- Python 3.12 exactly. It is possible later versions will work, but in the past some of our dependencies were not compatible with them.
- Poetry (Python package manager)

## Development Setup

1. Clone the repository:

   ```bash
   git clone git@github.com:crystaldba/crystaldba.git
   cd crystaldba/agent
   ```

2. Install dependencies using Poetry:

   ```bash
   poetry install
   ```

3. Copy the environment example file:

   ```bash
   cp env.example .env
   ```

4. Edit the `.env` file with your configuration:

## Environment Variables

See `agent/shared/constants.py` for current details.

#### Database to Monitor

- `DATABASE_URL`: PostgreSQL connection string (required)
  Example: `postgresql://user:password@localhost:5432/dbname`

## Running the Application

```bash
poetry run crystaldba
```

You can add `-v` or `-vv` in order to increase verbosity.

## Development Tools

- Code formatting and linting:

  ```bash
  poetry run ruff format .
  poetry run ruff check .
  ```

- Type checking:
  ```bash
  poetry run pyright
  ```

## Running Tests

Install test dependencies:

```bash
poetry install --with dev
```

Apply the required changes to the `.env` file.

Run unit tests:

```bash
poetry run pytest
```

Run unit tests with increased verbosity:

```bash
poetry run pytest -v
```
