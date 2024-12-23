#!/bin/bash

set -e

# Get the current directory
CURRENT_DIR=$(pwd)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
VERSION="0.7.0-rc0"
ARCH="amd64"
CONFIG_PATH="${CURRENT_DIR}/crystaldba.conf"

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]
Options:
    --config PATH          Path to crystaldba.conf file (default: ./crystaldba.conf)
    --version VERSION      Crystal DBA version (default: 0.7.0-rc0)
    --help                Show this help message
EOF
    exit 1
}

# Parse command line arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        --config=*)
            CONFIG_PATH="${1#*=}"
            ;;
        --version=*)
            VERSION="${1#*=}"
            ;;
        --help)
            show_usage
            ;;
        *)
            log_error "Unknown parameter: $1"
            show_usage
            ;;
    esac
    shift
done

# Check prerequisites
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo)"
    exit 1
fi

if [ ! -f "$CONFIG_PATH" ]; then
    log_error "Config file not found at: $CONFIG_PATH"
    exit 1
fi

# Install Crystal DBA Agent
log_info "Installing Crystal DBA Agent..."
cd ${CURRENT_DIR}
wget "https://github.com/crystaldb/crystaldba/releases/latest/download/crystaldba-${VERSION}-${ARCH}.tar.gz"
tar -xzvf "crystaldba-${VERSION}-${ARCH}.tar.gz"
cd "crystaldba-${VERSION}"
./install.sh --system

# Verify Crystal DBA Agent installation
if ! systemctl is-active --quiet crystaldba; then
    log_error "Crystal DBA Agent installation failed"
    exit 1
fi
log_info "Crystal DBA Agent installed successfully"

# Install Crystal DBA Collector
log_info "Installing Crystal DBA Collector..."
cd ${CURRENT_DIR}
wget "https://github.com/crystaldb/crystaldba/releases/latest/download/collector-${VERSION}-${ARCH}.tar.gz"
tar -xzvf "collector-${VERSION}-${ARCH}.tar.gz"
cd "collector-${VERSION}"
./install.sh --config "$CONFIG_PATH" --system

# Verify Crystal DBA Collector installation
if ! systemctl is-active --quiet crystaldba-collector; then
    log_error "Crystal DBA Collector installation failed"
    exit 1
fi
log_info "Crystal DBA Collector installed successfully"

# Clean up downloaded files
cd ${CURRENT_DIR}
rm -rf "crystaldba-${VERSION}" "collector-${VERSION}" "crystaldba-${VERSION}-${ARCH}.tar.gz" "collector-${VERSION}-${ARCH}.tar.gz"

log_info "Installation completed successfully!"
log_info "You can access the Crystal DBA web portal at http://localhost:4000"
log_warn "Please make sure to secure your installation and keep your credentials safe"
