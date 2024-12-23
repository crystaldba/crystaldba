# Integration tests

## Running the Tests

First, build the main project docker image with the image name name you will pass into the test suite
```bash
docker build -t crystaldba:latest ../
```
This image will be used by the test suite to create container instances to test against

To run the tests, use the following command structure, replacing the placeholders with your actual database details:
The dbconfig json is a map of postgres versions to details for a db of that version. This corelation will be validated in the tests

```bash

go test ./... -run TestAPISuite -v -timeout 20m -args -imageName crystaldba:latest -dbconfig='{
  "16": {
    "description": "PostgreSQL 16 instance",
    "host": "your-db-host",
    "name": "your-db-name",
    "username": "your-db-username",
    "password": "your-db-password",
    "port": "5432",
    "aws_rds_instance": "your-instance-id",
    "aws_region": "your-aws-region",
    "aws_access_key": "your-aws-access-key",
    "aws_secret": "your-aws-secret-key",
    "system_scope": "us-west-2/abcdefghijk",
    "system_type": "amazon_rds"
  }
}'
```


To test multiple postgres versions, create the appropriate databases and fill in the relevant information below

```bash
go test ./... -run TestAPISuite -v -timeout 20m -args -imageName crystaldba:latest -dbconfig='{
  "15": {
    "description": "PostgreSQL 15 instance",
    "host": "your-db-host",
    "name": "your-db-name",
    "username": "your-db-username",
    "password": "your-db-password",
    "port": "5432",
    "aws_rds_instance": "your-instance-id",
    "aws_region": "your-aws-region",
    "aws_access_key": "your-aws-access-key",
    "aws_secret": "your-aws-secret-key",
    "system_scope": "us-west-2/abcdefghijk",
    "system_type": "amazon_rds"
  },
  "14": {
    "description": "PostgreSQL 14 instance",
    "host": "your-db-host",
    "name": "your-db-name",
    "username": "your-db-username",
    "password": "your-db-password",
    "port": "5432",
    "aws_rds_instance": "your-instance-id",
    "aws_region": "your-aws-region",
    "aws_access_key": "your-aws-access-key",
    "aws_secret": "your-aws-secret-key",
    "system_scope": "us-west-2/abcdefghijk",
    "system_type": "amazon_rds"
  },
  "13": {
    "description": "PostgreSQL 13 instance",
    "host": "your-db-host",
    "name": "your-db-name",
    "username": "your-db-username",
    "password": "your-db-password",
    "port": "5432",
    "aws_rds_instance": "your-instance-id",
    "aws_region": "your-aws-region",
    "aws_access_key": "your-aws-access-key",
    "aws_secret": "your-aws-secret-key",
    "system_scope": "us-west-2/abcdefghijk",
    "system_type": "amazon_rds"
  }
}'
```
