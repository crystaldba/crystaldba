#!/bin/bash

# SPDX-Identifier: Apache-2.0

# Set the base directory based on installation
PARENT_DIR="${PARENT_DIR:-/usr/local/crystaldba}"

# Start the reloader service
$PARENT_DIR/bin/prometheus-reloader &

# Choose config file based on reprocessing status
if [ "${CRYSTALDBA_REPROCESS_FULL_SNAPSHOTS}" = "true" ] || [ "${CRYSTALDBA_REPROCESS_COMPACT_SNAPSHOTS}" = "true" ]; then
    CONFIG_SOURCE="$PARENT_DIR/config/prometheus/prometheus.reprocess.yml"
else
    CONFIG_SOURCE="$PARENT_DIR/config/prometheus/prometheus.normal.yml"
fi

# Copy the selected config to the final location
cp "$CONFIG_SOURCE" "$PARENT_DIR/config/prometheus/prometheus.yml"

# Start up Prometheus for initialization
"$PARENT_DIR/prometheus/prometheus" \
    --config.file="$PARENT_DIR/config/prometheus/prometheus.yml" \
    --storage.tsdb.path="$PARENT_DIR/prometheus_data" \
    --storage.tsdb.allow-overlapping-blocks \
    --query.lookback-delta="15m" \
    --web.console.templates="$PARENT_DIR/config/prometheus/consoles" \
    --web.console.libraries="$PARENT_DIR/config/prometheus/console_libraries" \
    --web.enable-remote-write-receiver \
    --web.enable-admin-api \
    --web.enable-lifecycle \
    --query.max-concurrency=4
