#!/bin/bash

# Directory to scan
DIRECTORY="${AUTODBA_STORAGE_DIR:-/usr/local/autodba/share/collector_api_server/storage}"

# GCS bucket name
BUCKET="${AUTODBA_GCS_BUCKET:-gs://crystaldb-production}"

# Cron job command - run every hour, process files older than 1 hour
CRON_JOB="0 * * * * /usr/bin/find $DIRECTORY ! -name '*.db' -mmin +60 -type f -exec sh -c 'gcloud storage cp \"{}\" $BUCKET/\$(basename \"{}\") && sudo rm \"{}\"' \;"

# Function to remove existing cron job if it exists
remove_cron_job() {
    # Remove the cron job if it exists
    crontab -l | grep -v "/usr/bin/find" | crontab -
}

# Function to create a new cron job
create_cron_job() {
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
}

# Main script execution
remove_cron_job
create_cron_job

echo "Cron job set to backup files to GCS bucket and delete local files older than 3 days."
