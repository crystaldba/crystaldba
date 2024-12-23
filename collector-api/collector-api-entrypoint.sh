#!/bin/bash

# SPDX-Identifier: Apache-2.0

# Set the base directory based on installation
PARENT_DIR="${PARENT_DIR:-/usr/local/crystaldba}"
PROMETHEUS_HOST="${PROMETHEUS_HOST:-localhost:9090}"

# Wait for Prometheus to be ready
echo "collector-api: Waiting for Prometheus to be ready..."
until curl -s ${PROMETHEUS_HOST}/-/ready > /dev/null; do
    sleep 1
done
echo "collector-api: Prometheus is ready."

cd $PARENT_DIR/share/collector_api_server

# Start the Collector API Server
exec ./collector-api-server  --reprocess-full=${CRYSTALDBA_REPROCESS_FULL_SNAPSHOTS:-false} --reprocess-compact=${CRYSTALDBA_REPROCESS_COMPACT_SNAPSHOTS:-false}
