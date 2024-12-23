#!/bin/bash

set -e

# Get the directory of the currently executing script
SOURCE_DIR=$(dirname "$(readlink -f "$0")")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Set default parent directory
PARENT_DIR="${PARENT_DIR:-/usr/local/crystaldba}"
REPROCESS_DONE_FILE="/tmp/crystaldba_reprocess_done"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Remove done file if it exists
rm -f "$REPROCESS_DONE_FILE"

# Stop services
log_info "Stopping Crystal DBA services..."
systemctl stop crystaldba

# Clean up Prometheus data
log_info "Cleaning up Prometheus data..."
if [ -d "$PARENT_DIR/prometheus_data" ]; then
    rm -rf "$PARENT_DIR/prometheus_data"/*
    log_info "Prometheus data directory cleaned"
else
    log_warn "Prometheus data directory not found at: $PARENT_DIR/prometheus_data"
fi

# Create override files for systemd services
log_info "Configuring reprocessing environment..."
mkdir -p /etc/systemd/system/crystaldba.service.d
cat << EOF > /etc/systemd/system/crystaldba.service.d/override.conf
[Service]
Environment="CRYSTALDBA_REPROCESS_FULL_SNAPSHOTS=true"
Environment="CRYSTALDBA_REPROCESS_COMPACT_SNAPSHOTS=true"
Environment="CRYSTALDBA_REPROCESS_DONE_FILE=${REPROCESS_DONE_FILE}"
EOF

# Reload systemd to pick up changes
log_info "Reloading systemd configuration..."
systemctl daemon-reload

# Start services with reprocessing flags
log_info "Starting services with reprocessing enabled..."
systemctl start crystaldba

# Wait for reprocessing to complete
log_info "Waiting for reprocessing to complete..."
while [ ! -f "$REPROCESS_DONE_FILE" ]; do
    echo -n "."
    sleep 5
done
echo # New line after dots

# Stop services again
log_info "Stopping services..."
systemctl stop crystaldba

# Remove override files
log_info "Removing reprocessing configuration..."
rm -rf /etc/systemd/system/crystaldba.service.d
rm -f "$REPROCESS_DONE_FILE"

# Reload systemd again
systemctl daemon-reload

# Start services normally
log_info "Starting services normally..."
systemctl start crystaldba

log_info "Reprocessing complete!"

$SOURCE_DIR/show-logs.sh
