#!/bin/bash

# SPDX-Identifier: Apache-2.0

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Initialize variables
SYSTEM_INSTALL=false
USER_INSTALL_DIR=""
CONFIG_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --system)
            SYSTEM_INSTALL=true
            shift
            ;;
        --install-dir)
            USER_INSTALL_DIR="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

usage() {
    echo "Usage: $0 [--system] [--install-dir <path>] [--config <config.conf>]"
    echo ""
    echo "Options:"
    echo "  --system       Install globally under /usr/local/crystaldba-collector"
    echo "  --install-dir  Specify a custom installation directory. If not specified, the current directory ($(pwd)) is used."
    echo "  --config       Path to the Crystal DBA config file (optional), or use standard input if not provided."
    exit 1
}

# Set the parent directory
if [ -n "$USER_INSTALL_DIR" ]; then
    PARENT_DIR="$USER_INSTALL_DIR"
elif [ "$SYSTEM_INSTALL" = true ]; then
    PARENT_DIR="/usr/local/crystaldba-collector"
else
    PARENT_DIR="$(pwd)"
fi

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Stop the service if it's already running
if $SYSTEM_INSTALL && command_exists "systemctl"; then
    if systemctl is-active --quiet crystaldba-collector; then
        echo "Stopping Crystal DBA Collector service..."
        systemctl stop crystaldba-collector
    fi
fi

# Set paths relative to PARENT_DIR
INSTALL_DIR="$PARENT_DIR"
CRYSTALDBA_CONFIG_DIR="$PARENT_DIR/config"
CRYSTALDBA_COLLECTOR_CONFIG_FILE="$CRYSTALDBA_CONFIG_DIR/collector.conf"

echo "Installing Crystal DBA Collector under: $PARENT_DIR"

mkdir -p "${CRYSTALDBA_CONFIG_DIR}"

# Create directories only if PARENT_DIR is not current directory
if [ "$PARENT_DIR" != "$(pwd)" ]; then
    echo "Copying files to installation directory..."
    mkdir -p "${PARENT_DIR}"
    mkdir -p "${INSTALL_DIR}"

    cp -r "${SCRIPT_DIR}"/* "${INSTALL_DIR}"
else
    echo "Using the current directory for installation, no copying needed."
fi

chmod +x "${INSTALL_DIR}/crystaldba-collector"
chmod +x "${INSTALL_DIR}/crystaldba-collector-helper"
chmod +x "${INSTALL_DIR}/crystaldba-collector-setup"
chmod +x "${INSTALL_DIR}/collector-entrypoint.sh"

# Handle configuration file
if [ -n "$CONFIG_FILE" ]; then
    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "${CRYSTALDBA_COLLECTOR_CONFIG_FILE}"
    else
        echo "Error: Config file $CONFIG_FILE does not exist."
        exit 1
    fi
elif [ ! -t 0 ]; then
    echo "Reading config from stdin and saving to $CRYSTALDBA_COLLECTOR_CONFIG_FILE"
    if ! cat > "$CRYSTALDBA_COLLECTOR_CONFIG_FILE"; then
        echo "Error: Failed to save stdin input to $CRYSTALDBA_COLLECTOR_CONFIG_FILE"
        exit 1
    fi
    echo "Crystal DBA Collector config saved at $CRYSTALDBA_COLLECTOR_CONFIG_FILE"
else
    echo "Error: no config file provided, and no input from stdin detected."
    exit 1
fi

# Systemctl service setup (if needed)
if $SYSTEM_INSTALL && command -v "systemctl" >/dev/null 2>&1; then
    if ! id -u crystaldba-collector >/dev/null 2>&1; then
        echo "Creating 'crystaldba-collector' user..."
        if command -v "useradd" >/dev/null 2>&1; then
            useradd --system --user-group --home-dir /usr/local/crystaldba-collector --shell /bin/bash crystaldba-collector
        elif command -v "adduser" >/dev/null 2>&1; then
            adduser --system --group --home /usr/local/crystaldba-collector --shell /bin/bash crystaldba-collector
        else
            echo "Error: Neither 'useradd' nor 'adduser' found. Please create the user manually."
            exit 1
        fi
    fi
    chown -R crystaldba-collector:crystaldba-collector "$PARENT_DIR"
    
    echo "Setting up systemd service..."
    cat << EOF | tee /etc/systemd/system/crystaldba-collector.service
[Unit]
Description=Crystal DBA Collector Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/collector-entrypoint.sh
Restart=on-failure
User=crystaldba-collector
Group=crystaldba-collector
Environment="CONFIG_FILE=${CRYSTALDBA_COLLECTOR_CONFIG_FILE}"

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable crystaldba-collector
    systemctl start crystaldba-collector
else
    echo "System installation not requested or systemctl is unavailable. Skipping systemd service setup."
    echo "You can run the following command to start the Crystal DBA Collector service manually:"
    echo "  cd \"${INSTALL_DIR}\" && CONFIG_FILE=\"${CRYSTALDBA_COLLECTOR_CONFIG_FILE}\" ./collector-entrypoint.sh"
fi

echo "Crystal DBA Collector installation complete!"
