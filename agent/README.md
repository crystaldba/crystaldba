# CrystalDBA Agent

## Prerequisites

- Python 3.12 exactly. It is possible later versions will work, but in the past some of our dependencies were not compatible with them.
- Poetry (Python package manager)
- PostgreSQL database

## Development Setup

1. Clone the repository:

   ```bash
   git clone git@github.com:crystaldba/crystaldba-demo.git
   cd crystaldba-demo
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

5. To install griptape in editable mode:
   ```bash
   poetry add --editable /path/to/griptape
   ```

## Environment Variables

See `agent/shared/constants.py` for current details.

### Server Configuration

- `CRYSTAL_API_PORT`: Server port (default: 8000)
- `CRYSTAL_API_HOST`: Server host binding (default: 0.0.0.0)
- `LOG_LEVEL`: Logging level (default: info)
- `CRYSTAL_BACKEND_DATABASE_URL`: PostgreSQL connection string (required) used by the server to store sessions
  Example: `postgresql://user:password@localhost:5444/dbname`

#### Database to Monitor

- `DATABASE_URL`: PostgreSQL connection string (required)
  Example: `postgresql://user:password@localhost:5432/dbname`

## The Server needs access to Postgres

You will need a local postgres server.

```
docker run --name postgres_registry -e POSTGRES_PASSWORD=mysecretpassword -p 5444:5432 -d postgres
```

Check your database connectivity, e.g.,

```
psql 'postgres://postgres:mysecretpassword@localhost:5444/postgres'
```

This is the connection string that you will set in CRYSTAL_BACKEND_DATABASE_URL in your `.env` file.

## Running the Application

1. Start the server:

For development mode with auto-reload:

```bash
poetry run python -m server.main dev
```

For production mode:

```bash
poetry run python -m server.main
```

2. In a separate terminal, run the client:

```bash
poetry run python -m client.main
```

You can add `-v` or `-vv` to both client and server in order to increase verbosity.

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

```bash
# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-REPLACE_ME
LANGFUSE_SECRET_KEY=sk-REPLACE_ME
LANGFUSE_HOST=https://us.cloud.langfuse.com

# Evaluation Configuration
# These are the databases that will be used for evaluation
TEST1_DATABASE_URL=postgresql://postgres:mysecretpassword@localhost:5432/postgres
# TEST2_DATABASE_URL=postgresql://postgres:mysecretpassword@localhost:5432/postgres
```

Run unit tests:

```bash
poetry run pytest
```

Run unit tests with increased verbosity:

```bash
poetry run pytest -v
```

Run Langfuse evaluation tests (requires OpenAI API key and Langfuse credentials):

```bash
poetry run pytest -m evaluation
```

Run (a) specific evaluation dataset(s):

```bash
poetry run pytest -m evaluation --datasets=<comma_separated_dataset_names>
```

Run with a specific label:

```bash
poetry run pytest -m evaluation --labels=<comma_separated_label_names>
```

Run with interactive logging (for debugging):

```bash
poetry run pytest -m evaluation --log-cli-level=INFO --datasets=<comma_separated_dataset_names>
```


Run all tests:

```bash
poetry run pytest && poetry run pytest -m integration && poetry run pytest -m evaluation
```

## Dataset Management

The project includes commands to manage test datasets using Langfuse. GitHub is the single source of truth, with JSON files providing a convenient way to work offline and version changes.


### Downloading Datasets

To download a dataset from Langfuse:

```bash
poetry run pull_dataset <dataset_name>
```

This will:
- Download the specified dataset from Langfuse
- Save it as a JSON file in the `datasets` directory
- Format the data for use with the testing framework

The output JSON file will be in the `datasets` directory, with the same name as the dataset.

### Uploading Datasets

To upload a dataset to Langfuse:

```bash
poetry run push_dataset <dataset_name>
```

Parameters:
- `dataset_name`: Name for the dataset in Langfuse. There should be a JSON file in the `datasets` directory with the same name.

### Dataset Format

Datasets are stored as JSON files in the `datasets` directory with the following format:

```json
{
  "metadata": {
    "description": "dataset_description",
    "db_env_var_name": "TEST1_DATABASE_URL",
    ...
  },
  "items": [
    {
      "name": "test_case_1",
      "input": "input data",
      "expected_output": "expected output",
      "metadata": {
        "skip": false,
        "labels": ["chapter5", "shortquery"],
        ...
      }
    }
  ]
}
```

Key features:
  - The JSON file name is the dataset name
  - `skip`: Set to `true` to exclude a test case from evaluation
  - `labels`: Array of strings used to filter and run specific test cases
  - Additional metadata can be added at both dataset and item levels

### Running Evaluations

To run evaluations with specific filters:

```bash
poetry run pytest -m evaluation \
    --log-cli-level=INFO \
    --datasets=<dataset_name>[,dataset_name]* \
    [--labels=<label_name>[,label_name]*]
```

This will:
  - Only run test cases with specified labels (if --labels is provided)
  - Skip test cases marked with `"skip": true`
  - Show detailed logging output

### Dataset Collaboration

To collaborate on a dataset, follow these steps:

1. Create a git branch from `demo-main` for your changes:
   ```bash
   git checkout demo-main
   git checkout -b mybranch
   ```

2. Modify the tests locally in your `datasets/<dataset_name>.json` file.

   Note: To skip a test case, set the `skip` field (under `metadata`) to `true`.

3. Run the evaluation:
   ```bash
   poetry run pytest -m evaluation --datasets=<dataset_name> --log-cli-level=INFO
   ```

   This command will:
   - Push your local dataset to Langfuse with the name `mybranch-<dataset_name>` (if it doesn't exist)
   - Pull the `mybranch-<dataset_name>` dataset back from Langfuse
     (this ensures you have any changes made via the Langfuse UI)
   - Evaluate the dataset named `mybranch-<dataset_name>` on Langfuse

4. Create a Pull Request with your changes:
   - Create a PR from your branch to `demo-main`
   - Include a link to the Langfuse dataset (`mybranch-<dataset_name>`) in your PR description
   - This allows reviewers to examine the latest evaluation results for your dataset

5. After the PR is merged into `demo-main`:
   - Delete the `mybranch-<dataset_name>` dataset from Langfuse
   - Switch to the demo-main branch:
     ```bash
     git checkout demo-main
     ```
   - Run the evaluation again:
     ```bash
     poetry run pytest -m evaluation --datasets=<dataset_name> --log-cli-level=INFO
     ```
     
     This final evaluation will:
     - Push the local dataset to Langfuse with the name `<dataset_name>` (if it doesn't exist)
     - Pull the `<dataset_name>` dataset back from Langfuse
     - Evaluate the dataset
     
     Note: If you see any changes in this step (usually due to test case reordering), 
     create another PR with these updates to keep the repository in sync.

## A note about Griptape

The poetry `pyproject.json` installs Griptape.
We do not really need all of Griptape's capabilities, but it's convenient for development to have them all installed.

Using a cloned copy can be useful during development because you can make changes to Griptape and see them immediately.
Navigate to the directory of your choice, then clone Griptape and install it

```
git clone https://github.com/griptape-ai/griptape.git
cd griptape
pip install poetry
poetry install --all-extras --with dev --with test --with docs
```
