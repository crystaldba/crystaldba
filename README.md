![Build Status](https://github.com/crystaldba/crystaldba/actions/workflows/build.yml/badge.svg)

# 🤖 Crystal DBA for PostgreSQL 🐘

Crystal DBA is an AI teammate for PostgreSQL database administration.
We aim to ensure that everyone who runs PostgreSQL has access to a AI-powered database expertise at all times.

**Quick install**

Requires Python 3.10+ and [pipx](https://pipx.pypa.io/latest/) to be installed.

```bash
# Using pipx (recommended)
pipx install crystaldba

# Using Docker
docker pull crystaldba/crystaldba:latest
docker run -it --rm crystaldba/crystaldba
```

Here is an example controlling where the Crystal API server is running and a local database. Feel free to modify to suit your needs:

```bash
docker pull crystaldba/crystaldba && docker run -it --rm -e CRYSTAL_API_URL=http://localhost:7080 crystaldba/crystaldba "postgresql://postgres:mysecretpassword@localhost:5444/postgres"
```

**Useful links**

- [Installation instructions](https://www.crystaldba.ai/docs/installation)
- [Getting started guide](https://www.crystaldba.ai/docs/getting-started)
- [Full documentation](https://www.crystaldba.ai/docs/)
- [FAQ](https://www.crystaldba.ai/docs/frequently-asked-questions)

## 💡 Motivation

We all want our production PostgreSQL databases to run well—they should be reliable, performant, efficient, scalable, and secure.
If your team is fully staffed with database administrators, then you are in luck.
If not, you may find yourself working reactively, dealing with problems as they arise and looking up what to do as you go.

Oftentimes, operational responsibility for databases falls to software engineers and site reliability engineers, who usually have many other things to do.
They have better ways to spend their time than tuning or troubleshooting databases.

Reliability and security are the top priorities for database operations.
We focus on these first, to provide a solid foundation for delivering trustworthy suggestions for performance and efficiency.
Crystal DBA is designed to give you advice on how to improve your database, but it will not take actions automatically without your review and consent.

## 🧑‍💻 About the Authors

Crystal DBA is developed by the engineers and database experts at [Crystal DBA](https://www.crystaldba.ai/).
Our mission is to make it easy for you to run your database well, so you can focus on building better software.
Crystal DBA also offers commercial support for Crystal DBA and PostgreSQL.

## 📖 Frequently Asked Questions

### What is Crystal DBA?

Crystal DBA is an AI agent for operating PostgreSQL databases.
This means that it connects to an existing PostgreSQL database and takes actions, as necessary, to ensure that the database remains reliable, efficient, scalable, and secure.

### Will Crystal DBA replace my DBA?

Time will tell whether AI agents completely replace human database administrators (DBAs).
Our work suggests that AI agents will do some tasks much better than humans.
They can find patterns across large amounts of data, they are always available, and they respond instantly.
They can also draw upon extensive knowledge bases and operational datasets, allowing them to proceed with less trial and error than people.

On the other hand, people working in the team will have a more nuanced understanding of the needs of the business.
They will be better able to make high-level design decisions and to analyze trade-offs that impact the development process.

### Do I still need to hire a DBA if I use Crystal DBA?

If you do not already have a DBA on staff, then chances are good that Crystal DBA can allow you to postpone hiring one, particularly if you have platform engineers or site reliability engineers who are interested in applying its recommendations.
Crystal DBA and others also offer commercial support for PostgreSQL.

### Which PostgreSQL versions are supported?

Currently, Crystal DBA is compatible with PostgreSQL versions 13 through 17.

### Can I use Crystal DBA with my on-premises PostgreSQL installation?

At present, Crystal DBA only works with AWS RDS PostgreSQL.
Support for on-premises installations, Google Cloud SQL, and Azure SQL is coming.
We want Crystal DBA to run anywhere that PostgreSQL runs.

### Will Crystal DBA support databases other than PostgreSQL?

At present, we are fully focused on Crystal DBA for PostgreSQL.
We expect to maintain that focus for the foreseeable future.

### Is Crystal DBA open source?

We believe that every PostgreSQL database should be managed by an AI agent.
In pursuit of this vision, we are releasing the core operational features of Crystal DBA under the Apache 2.0 open source license.

For avoidance of doubt, Crystal DBA is commercial open source software.
Certain enterprise features will be available only in commercial versions of the product.

As of this writing (August 2024), there is active debate what the term “open source” means for AI models.
Is a model open if the developer releases the weights but not the training data and methods?

We are committed to providing open weights and some training data.
However, we also expect to release models trained on proprietary data sets.

### How can I get support for Crystal DBA?

Crystal DBA offers commercial support for Crystal DBA and PostgreSQL.
For more information or to discuss your needs, please contact us at [support@crystaldba.ai](mailto:support@crystaldba.ai).

### How can I support the Crystal DBA project?

Foremost, use Crystal DBA and give us feedback!

We also welcome feature suggestions, bug reports, or contributions to the codebase.

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

```text
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
