# Crystal DBA Agent Command Line Interface


[Crystal DBA](https://www.crystaldba.ai) is an AI teammate for PostgreSQL database administration.
For more information, see the [documentation](https://www.crystaldba.ai/docs).

Installation:

```
pipx install crystaldba
```

See the [website installation instructions](https://www.crystaldba.ai/docs/installation) for further details.

Usage:

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


