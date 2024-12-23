#!/bin/bash

# SPDX-Identifier: Apache-2.0

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Initialize variables
SYSTEM_INSTALL=false
USER_INSTALL_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --system)
            SYSTEM_INSTALL=true
            PARENT_DIR="/usr/local/crystaldba"
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

# Set the parent directory
if [ -n "$USER_INSTALL_DIR" ]; then
    PARENT_DIR="$USER_INSTALL_DIR"
elif [ "$SYSTEM_INSTALL" = true ]; then
    PARENT_DIR="/usr/local/crystaldba"
else
    PARENT_DIR="$(pwd)"
fi

# Define paths under the parent crystaldba directory
INSTALL_DIR="${PARENT_DIR}/bin"
WEBAPP_DIR="${PARENT_DIR}/share/webapp"
CONFIG_DIR="${PARENT_DIR}/config"
PROMETHEUS_CONFIG_DIR="${CONFIG_DIR}/prometheus"
PROMETHEUS_DIR="${PARENT_DIR}/prometheus"
PROMETHEUS_STORAGE_DIR="${PARENT_DIR}/prometheus_data"
SYSTEMD_SERVICE="/etc/systemd/system/crystaldba.service"

echo "Uninstalling Crystal DBA from ${PARENT_DIR}..."

# Stop the service if systemd is used
if [ "$SYSTEM_INSTALL" = true ] && [ -f "$SYSTEMD_SERVICE" ]; then
    echo "Stopping and disabling Crystal DBA service..."
    sudo systemctl stop crystaldba
    sudo systemctl disable crystaldba
    sudo rm -f "$SYSTEMD_SERVICE"
    sudo systemctl daemon-reload
fi

if [ "$PARENT_DIR" != "$(pwd)" ]; then
    # Remove binaries and scripts
    echo "Removing binaries and scripts..."
    [ -d "${INSTALL_DIR}" ] && rm -rf "${INSTALL_DIR}" || true

    # Remove web application files
    echo "Removing web application files..."
    [ -d "${WEBAPP_DIR}" ] && rm -rf "${WEBAPP_DIR}" || true

    # Remove Prometheus configuration and storage
    echo "Removing Prometheus configuration and storage..."
    [ -d "${PROMETHEUS_DIR}" ] && rm -rf "${PROMETHEUS_DIR}" || true
    [ -d "${PROMETHEUS_CONFIG_DIR}" ] && rm -rf "${PROMETHEUS_CONFIG_DIR}" || true
    [ -d "${PROMETHEUS_STORAGE_DIR}" ] && rm -rf "${PROMETHEUS_STORAGE_DIR}" || true

    # Remove Crystal DBA configuration files
    echo "Removing Crystal DBA configuration files..."
    [ -d "${CONFIG_DIR}" ] && rm -rf "${CONFIG_DIR}" || true

    # Remove parent directory if empty
    if [ -d "${PARENT_DIR}" ]; then
        echo "Removing parent Crystal DBA directory..."
        rmdir --ignore-fail-on-non-empty "${PARENT_DIR}" || true
    fi

    echo "Removing tmp directories..."
    rm -rf /tmp/crystaldba-* /tmp/prometheus-* || true
else
    echo "Not removing the current directory as it is the installation directory."
fi

echo "Crystal DBA has been successfully uninstalled."
