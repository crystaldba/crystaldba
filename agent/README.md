# Crystal DBA Text User Interface (TUI)

[Crystal DBA](https://www.crystaldba.ai) is an AI teammate for PostgreSQL database administration.
For more information, see the [documentation](https://www.crystaldba.ai/docs).

## Installation

### Using pipx (recommended)

If you already have Python version >= 3.10 installed, then pipx is the easiest method to use (Python < 3.10 will not work).

```bash
pipx install crystaldba
```

See the [website installation instructions](https://www.crystaldba.ai/docs/installation) for further details.

### Using Docker

We provide multi-architecture Docker images (amd64 and arm64) for easy usage without installation:

```bash
# Pull the Docker image
docker pull crystaldba/crystaldba:latest

# Run the CLI
docker run -it --rm crystaldba/crystaldba
```

Here is an example controlling where the Crystal API server is running and a local database. Feel free to modify to suit your needs:

```bash
docker run -it --rm -e CRYSTAL_API_URL=http://localhost:7080 crystaldba/crystaldba "postgresql://postgres:mysecretpassword@localhost:5444/postgres"
```

Alternatively, build from source:

```bash
# Build the Docker image
docker build -t crystaldba/crystaldba .

# Run the CLI
docker run -it --rm crystaldba/crystaldba
```

## Docker Usage Guide

### Running during development

```bash
docker build -t crystaldba/crystaldba . && docker run -it --rm -e CRYSTAL_API_URL=http://localhost:7080 crystaldba/crystaldba "postgresql://postgres:mysecretpassword@localhost:5444/postgres"
```

> **Note:** Our Docker image automatically detects and handles connections to localhost in both the CRYSTAL_API_URL and database connection strings. It will remap these automatically to the appropriate Docker host address (host.docker.internal on Mac/Windows, or 172.17.0.1 on Linux).

### Cross-platform Usage

The Docker container automatically detects and handles connections to services running on your host machine:

- **Mac & Windows**: Uses `host.docker.internal` automatically
- **Linux Docker Desktop**: Uses `172.17.0.1` or `host.docker.internal` automatically
- **Linux Standard Docker**: May use `172.17.0.1` or need container networking options

### Basic Usage

Run with default settings:

```bash
docker run -it --rm crystaldba/crystaldba
```

### Connection Options

Connect to a specific database using URI:

```bash
docker run -it --rm crystaldba/crystaldba postgresql://username:password@hostname:port/dbname
```

Or using individual connection parameters:

```bash
docker run -it --rm crystaldba/crystaldba -h hostname -p 5432 -U username -d dbname
```

### Custom API URL

Override the default API endpoint:

```bash
docker run -it --rm -e CRYSTAL_API_URL=http://your-api-server:port crystaldba/crystaldba
```

### Additional Options

Set verbosity level:

```bash
# INFO level
docker run -it --rm crystaldba/crystaldba -v dbname

# DEBUG level
docker run -it --rm crystaldba/crystaldba -vv dbname
```

### Network Considerations

When connecting to services on your host machine from Docker, our entrypoint script automatically handles most cases:

```bash
# Works on all platforms - localhost is automatically remapped
docker run -it --rm crystaldba/crystaldba postgresql://username:password@localhost:5432/dbname
```

If you encounter connection issues, you can manually specify the host:

```bash
# Mac/Windows/Docker Desktop
docker run -it --rm crystaldba/crystaldba postgresql://username:password@host.docker.internal:5432/dbname

# Traditional Linux Docker
docker run -it --rm crystaldba/crystaldba postgresql://username:password@172.17.0.1:5432/dbname
```

The `--network=host` flag is generally not needed and should only be used if the automatic remapping doesn't work.

## CLI Usage

```
usage: crystaldba [-h HOSTNAME] [-p PORT] [-U USERNAME] [-d DBNAME] [-v] [--help] [DBNAME | URI]

Crystal DBA is an AI-powered postgreSQL expert.

Examples:
  crystaldba dbname
  crystaldba postgres://<username>:<password>@<host>:<port>/<dbname>
  crystaldba -d dbname -u dbuser

Connection options:
  DBNAME | URI          database name or URI to connect to
  -h HOSTNAME, --host HOSTNAME
                        database server host or socket directory (default: "localhost")
  -p PORT, --port PORT  database server port (default: "5432")
  -U USERNAME, -u USERNAME, --username USERNAME
                        database user name (default: "postgres")
  -d DBNAME, --dbname DBNAME
                        database name (default: "postgres")

Other options:
  -v, --verbose         increase verbosity level (-v: INFO, -vv: DEBUG)
  --help                show this help message and exit

Contact us:
  Email support@crystaldba.ai if you have questions.
```

## Pushing to Dockerhub

Replace "0.9.1..." version below with current version to push.

```bash
cd agent && just build-and-push v0.9.1rcVERSION
```
