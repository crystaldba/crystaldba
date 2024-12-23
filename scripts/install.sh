#!/bin/bash

# SPDX-Identifier: Apache-2.0

set -e

# Initialize variables
SYSTEM_INSTALL=false
USER_INSTALL_DIR=""

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
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

usage() {
    echo "Usage: $0 [--system] [--install-dir <path>]"
    echo ""
    echo "Options:"
    echo "  --system       Install globally under /usr/local/crystaldba"
    echo "  --install-dir  Specify a custom installation directory. If not specified, $HOME/crystaldba is used."
    exit 1
}

# Set the parent directory
if [ -n "$USER_INSTALL_DIR" ]; then
    PARENT_DIR="$USER_INSTALL_DIR"
elif [ "$SYSTEM_INSTALL" = true ]; then
    PARENT_DIR="/usr/local/crystaldba"
else
    PARENT_DIR="$(pwd)"
fi

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Stop the service if it's already running
if $SYSTEM_INSTALL && command_exists "systemctl"; then
    if systemctl is-active --quiet crystaldba; then
        echo "Stopping Crystal DBA service..."
        systemctl stop crystaldba
    fi
fi

# Set paths relative to PARENT_DIR
INSTALL_DIR="$PARENT_DIR/bin"
WEBAPP_DIR="$PARENT_DIR/share/webapp"
PROMETHEUS_CONFIG_DIR="$PARENT_DIR/config/prometheus"
CRYSTALDBA_CONFIG_DIR="$PARENT_DIR/config/crystaldba"
CRYSTALDBA_DATA_PATH="$PARENT_DIR/share/collector_api_server/storage"
PROMETHEUS_STORAGE_DIR="$PARENT_DIR/prometheus_data"
PROMETHEUS_INSTALL_DIR="$PARENT_DIR/prometheus"

echo "Installing Crystal DBA Agent under: $PARENT_DIR"

# Create directories only if PARENT_DIR is not current directory
if [ "$PARENT_DIR" != "$(pwd)" ]; then
    echo "Copying files to installation directory..."
    mkdir -p "${PARENT_DIR}"

    cp -r ./* "$PARENT_DIR"
else
    echo "Using the current directory for installation, no copying needed."
fi

chmod +x "${INSTALL_DIR}/crystaldba-entrypoint.sh"
chmod +x "${INSTALL_DIR}/prometheus-entrypoint.sh"
chmod +x "${INSTALL_DIR}/collector-api-entrypoint.sh"
chmod +x "${INSTALL_DIR}/bff-entrypoint.sh"

# Systemctl service setup (if needed)
if $SYSTEM_INSTALL && command_exists "systemctl"; then
    if ! id -u crystaldba >/dev/null 2>&1; then
        echo "Creating 'crystaldba' user..."

        if command_exists "useradd"; then
            useradd --system --user-group --home-dir /usr/local/crystaldba --shell /bin/bash crystaldba
        elif command_exists "adduser"; then
            adduser --system --group --home /usr/local/crystaldba --shell /bin/bash crystaldba
        else
            echo "Error: Neither 'useradd' nor 'adduser' found. Please create the user manually."
            exit 1
        fi
    fi

    # Remove override files
    rm -rf /etc/systemd/system/crystaldba.service.d

    chown -R crystaldba:crystaldba "$PARENT_DIR"
    echo "Setting up systemd service..."
    cat << EOF | tee /etc/systemd/system/crystaldba.service
[Unit]
Description=Crystal DBA Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${CRYSTALDBA_CONFIG_DIR}
ExecStart=${INSTALL_DIR}/crystaldba-entrypoint.sh
Restart=on-failure
User=crystaldba
Group=crystaldba
Environment="PARENT_DIR=${PARENT_DIR}"
Environment="CRYSTALDBA_DATA_PATH=${CRYSTALDBA_DATA_PATH}"

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable crystaldba
    systemctl start crystaldba
else
    echo "System installation not requested or systemctl is unavailable. Skipping systemd service setup."
    echo "You can run the following command to start the Crystal DBA service manually:"
    
    echo "  cd \"${CRYSTALDBA_CONFIG_DIR}\" && PARENT_DIR=\"${PARENT_DIR}\" CRYSTALDBA_DATA_PATH=\"${CRYSTALDBA_DATA_PATH}\" ${INSTALL_DIR}/crystaldba-entrypoint.sh"
fi

echo "Installation complete!"
