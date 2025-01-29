# Team Installation

This file documents the [team deployment model](https://www.crystaldba.ai/docs/user-guide/deployment-models/team) for Crystal DBA.

## 🚀 Quick Installation

1. Run these SQL commands to enable `pg_stat_statements` and create a monitoring user (replace `'YOUR_CRYSTALDBA_PASSWORD'` with your desired password for that user):
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT * FROM pg_stat_statements LIMIT 1;

CREATE USER crystaldba WITH PASSWORD 'YOUR_CRYSTALDBA_PASSWORD' CONNECTION LIMIT 5;
GRANT pg_monitor TO crystaldba;
GRANT USAGE ON SCHEMA public TO crystaldba;
```

2. Create a `crystaldba.conf` file with your database connection details:
```conf
[crystaldba]
api_key = DEFAULT-API-KEY
api_base_url = http://localhost:7080

[server1]
db_host = <YOUR_PG_DATABASE_HOST>
db_name = <YOUR_PG_DATABASE_NAME>
db_username = crystaldba
db_password = <YOUR_CRYSTALDBA_PASSWORD>
db_port = 5432
# For AWS RDS:
aws_db_instance_id = <YOUR_AWS_RDS_INSTANCE_ID>
aws_region = <YOUR_AWS_REGION>
# For Google Cloud SQL:
# gcp_project_id = <YOUR_GCP_PROJECT_ID>
# gcp_cloudsql_instance_id = <YOUR_GCP_CLOUDSQL_INSTANCE_ID>
```

3. Install the latest agent and collector:
```bash
sudo /bin/bash -c "$(curl https://raw.githubusercontent.com/crystaldba/crystaldba/refs/heads/main/scripts/install_release.sh)"
```

For detailed installation instructions, including cloud provider setup and additional configuration options, see the [Detailed Installation](#detailed-installation) section below.

## 💻 Detailed Installation

### Prerequisites

1. *Linux server* with network access to your PostgreSQL database.
We recommend using a machine with at least 2&nbsp;GB of RAM and 10&nbsp;GB of disk space (e.g., `t3.small` on AWS, `e2-small` on GCP).

2. *Enabling pg_stat_statements*: connect to your database using psql, and run the following SQL commands to enable the pg_stat_statements extension, and make sure it works:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT * FROM pg_stat_statements LIMIT 1;
```

3. *Monitoring DB user*: connect to your database using psql. Then run the following to create a monitoring user. Replace 'YOUR_CRYSTALDBA_PASSWORD' with your desired password for that user:

```sql
CREATE USER crystaldba WITH PASSWORD 'YOUR_CRYSTALDBA_PASSWORD' CONNECTION LIMIT 5;
GRANT pg_monitor TO crystaldba;
GRANT USAGE ON SCHEMA public TO crystaldba;
```

4. AWS or Google Cloud credentials with permissions to read database metrics

### Crystal DBA Agent Installation

Follow these instructions to install Crystal DBA Agent on Linux.

1. Download the latest release of Crystal DBA Agent from the [releases page](https://github.com/crystaldba/crystaldba/releases).
Choose the version appropriate to your architecture and operating system.
For example:

```bash
wget https://github.com/crystaldba/crystaldba/releases/latest/download/crystaldba-svc-0.8.0rc6-amd64.tar.gz
```

2. Extract the downloaded tar.gz file:
```bash
tar -xzvf crystaldba-svc-0.8.0rc6-amd64.tar.gz
cd crystaldba-svc-0.8.0rc6
```

3. Run the `install.sh` script to install Crystal DBA Agent.

For system-wide installation:

```bash
sudo ./install.sh --system
```

Or for a user-specific installation, specify your preferred install directory:

```bash
./install.sh --install-dir "$HOME/crystaldba"
```

Or to install in the same extracted directory:
```bash
./install.sh
```

4. Verify the Crystal DBA service is running

```bash
systemctl is-active crystaldba
```

5. Take a look at the Crystal DBA service logs:
```
sudo journalctl -xefu crystaldba.service
```

This command should output `active`.

6. Connect to the Crystal DBA web portal on port 4000. If you have installed Crystal DBA on a remote server you can use [ssh tunneling](https://www.ssh.com/academy/ssh/tunneling-example) to access it.
For example:
```
ssh -L4000:localhost:4000 <MY_USERNAME>@<MY_HOSTNAME>
```

### Cloud Access Setup

We'll set up the roles/policies in your cloud provider, so that the collector can access database metrics and logs.  Jump below to the section for your cloud provider (AWS or GCP).

#### Amazon Web Services (AWS)

##### Create IAM policy

We'll create an IAM policy that allows the collector to view RDS instances, CloudWatch metrics and RDS log files.

First, save this JSON to a file called **crystaldba_policy.json**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "cloudwatch:GetMetricStatistics"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Action": [
        "logs:GetLogEvents"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:logs:*:*:log-group:RDSOSMetrics:log-stream:*"
    },
    {
      "Action": [
        "rds:DescribeDBParameters"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:rds:*:*:pg:*"
    },
    {
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DownloadDBLogFilePortion",
        "rds:DescribeDBLogFiles"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:rds:*:*:db:*"
    },
    {
      "Action": [
        "rds:DescribeDBClusters"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:rds:*:*:cluster:*"
    }
  ]
}
```

Then, run this command from the CLI:

```bash
aws iam create-policy
    --policy-name crystaldba
    --policy-document file://crystaldba_policy.json
    --description "Allow Crystal DBA to access RDS"
```

##### Create IAM role

First, run this command to create the IAM role:

```bash
aws iam create-role
    --role-name crystaldba
    --description "crystaldba collector"
    --assume-role-policy-document '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]}'
```

Then, run this command to attach the policy, after replacing `AWS_ACCOUNT_ID`:

```bash
aws iam attach-role-policy
    --role-name crystaldba
    --policy-arn arn:aws:iam::AWS_ACCOUNT_ID:policy/crystaldba
```

##### Attach IAM role to EC2 instance

Either start a new `t3.small` EC2 instance and attach the IAM role during creation or attach the IAM role to an existing instance with the following command:

```bash
aws ec2 associate-iam-instance-profile
    --instance-id INSTANCE_ID
    --iam-instance-profile Name=crystaldba
```

Continue to the **Collector Installation** section.

#### Google Cloud Platform (GCP)

##### Create Service Account

Create a new service account for Crystal DBA with the following command:

```bash
gcloud iam service-accounts create crystaldba --display-name "Crystal DBA"
```

##### Add Roles to the Service Account

We will add the following roles to the service account:

- Cloud SQL Viewer & Client
- Monitoring Service Agent
- Pub/Sub Subscriber

To add the roles use the following commands, replacing `PROJECT_ID`:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:crystaldba@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.viewer"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:crystaldba@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:crystaldba@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.notificationServiceAgent"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:crystaldba@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.subscriber"
```

##### Set up CloudSql logs

We'll use a Pub/Sub topic to collect logs from the CloudSQL instance.

First, create a Pub/Sub topic for the logs:

```bash
gcloud pubsub topics create crystaldba-cloudsql-logs
```

Then, create a subscription to the topic:

```bash
gcloud pubsub subscriptions create crystaldba-cloudsql-logs-sub --topic crystaldba-cloudsql-logs --message-retention-duration=1d
```

Write down the `SUBSCRIPTION_NAME` that is output from the previous command, as you will need it later for the collector configuration. The output will look something like this:

```
Created subscription [SUBSCRIPTION_NAME].
```


Then, set up a logging sink to publish logs from the CloudSQL instance to the topic, replacing `PROJECT_ID` and `CLOUDSQL_INSTANCE_ID`:

```bash
gcloud logging sinks create crystaldba-cloudsql-logs-sink \
    pubsub.googleapis.com/projects/PROJECT_ID/topics/crystaldba-cloudsql-logs \
    --log-filter='resource.type="cloudsql_database" resource.labels.database_id="CLOUDSQL_INSTANCE_ID"'
```

##### Attach Service Account to GCE instance

You will need at least a `e2-small` GCE instance and need to attach the service account that we created earlier.

If you're creating a new instance, you can attach the service account with the `service-account` flag. Something like this, replacing `PROJECT_ID`:

```bash
gcloud compute instances create \
    --service-account="crystaldba@PROJECT_ID.iam.gserviceaccount.com"
```

If you are attaching the service account to an existing instance, run the following command, replacing `INSTANCE_ID`, `INSTANCE_ZONE`, and `PROJECT_ID`:

```bash
gcloud compute instances set-service-account INSTANCE_ID \
    --zone=INSTANCE_ZONE \
    --service-account=crystaldba@PROJECT_ID.iam.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/cloud-platform
```


### Crystal DBA Collector Installation


Follow these instructions to install Crystal DBA Collector on Linux.

1. Download the latest release of Crystal DBA Collector from the [releases page](https://github.com/crystaldba/crystaldba/releases).
Choose the version appropriate to your architecture and operating system.
For example:

```bash
wget https://github.com/crystaldba/crystaldba/releases/latest/download/collector-0.8.0rc6-amd64.tar.gz
```

2. Extract the downloaded tar.gz file:
```bash
tar -xzvf collector-0.8.0rc6-amd64.tar.gz
cd collector-0.8.0rc6
```

3. Run this command to create a configuration file (`crystaldba.conf`) and populate it with values appropriate to your environment:

```conf
cat << EOF > crystaldba.conf
[crystaldba]
api_key = DEFAULT-API-KEY
api_base_url = <YOUR_CRYSTALDBA_API_BASE_URL, e.g., http://localhost:7080 or http://crystaldba-agent:7080 (if you are using run.sh)>

[server1]
db_host = <YOUR_PG_DATABASE_HOST, e.g., xyz.abcdefgh.us-west-2.rds.amazonaws.com>
db_name = <YOUR_PG_DATABASE_NAMES, e.g., postgres>
db_username = <YOUR_PG_DATABASE_USER_NAME, e.g., postgres>
db_password = <YOUR_PG_DATABASE_PASSWORD>
db_port = <YOUR_PG_DATABASE_PASSWORD, e.g., 5432>
aws_db_instance_id = <YOUR_AWS_RDS_INSTANCE_ID, e.g., xyz>
aws_region = <YOUR_AWS_RDS_REGION, e.g., us-west-2>
aws_access_key_id = <YOUR_AWS_ACCESS_KEY_ID>
aws_secret_access_key = <YOUR_AWS_SECRET_ACCESS_KEY>

# You can optionally add more servers by adding more sections similar to the above, but with parameters for Google Cloud SQL
# [server2]
# db_host = <YOUR_PG_DATABASE_HOST, e.g., localhost>
# db_name = <YOUR_PG_DATABASE_NAMES, e.g., postgres>
# db_username = <YOUR_PG_DATABASE_USER_NAME, e.g., postgres>
# db_password = <YOUR_PG_DATABASE_PASSWORD>
# db_port = <YOUR_PG_DATABASE_PASSWORD, e.g., 5432>
# gcp_project_id = <YOUR_GCP_PROJECT_ID>
# gcp_cloudsql_instance_id = <YOUR_GCP_CLOUDSQL_INSTANCE_ID>
# gcp_credentials_file = <YOUR_GCP_CREDENTIALS_FILE (default value: ~/.config/gcloud/application_default_credentials.json)>
# gcp_pubsub_subscription = <YOUR_GCP_PUBSUB_SUBSCRIPTION_NAME>
EOF
```

#### Notes:
  - `api_base_url` should be the URL for `Crystal DBA Agent` installed in the previous section.

  - If you have a PostgreSQL connection string (i.e., URI) of the form `postgres://<db_username>:<db_password>@<db_host>:<db_port>/<db_name>` you can extract `db_username`, `db_password`, `db_host`, `db_port`, and `db_name`.

  - If you're using AWS RDS, then your `<db_host>` is in this format: `<aws_db_instance_id>.<aws_account_id>.<aws_region>.rds.amazonaws.com`

  - For Google Cloud `gcp_pubsub_subscription` use the Pub/Sub subscription that we created in the previous section.

  - For Google Cloud SQL, you need to follow [these instructions](https://cloud.google.com/sql/docs/postgres/connect-auth-proxy#install) to install cloud-sql-proxy on your GCE instance (if your database is not directly accessible from this machine). Then, you need to:
    - Run the proxy: `./cloud-sql-proxy --port <YOUR_PROXIED_DB_PORT> <YOUR_GCP_PROJECT_ID>:<YOUR_GCP_CLOUDSQL_INSTANCE_ID> &`.
    - Then, in the configuration file (`crystaldba.conf`), you should set `db_host = localhost`, and `db_port = <YOUR_PROXIED_DB_PORT>`.
    - You'll want to set up the proxy to run as a service on startup.

#### Install the Collector:

4. Run the `install.sh` script to install Crystal DBA Collector.

For system-wide installation:

```bash
sudo ./install.sh --config crystaldba.conf --system
```

Or for a user-specific installation, specify your preferred install directory:

```bash
./install.sh --config crystaldba.conf --install-dir "$HOME/crystaldba-collector"
```

Or to install in the same extracted directory:
```bash
./install.sh --config crystaldba.conf
```

5. Verify the Crystal DBA service is running

```bash
systemctl is-active crystaldba-collector
```

6. Take a look at the Crystal DBA service logs:
```
sudo journalctl -xefu crystaldba-collector.service
```

This command should output `active`.
