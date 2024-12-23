#!/bin/bash

# SPDX-Identifier: Apache-2.0

set -e

# Get the directory of the currently executing script
SOURCE_DIR=$(dirname "$(readlink -f "$0")")

cd $SOURCE_DIR/..

# Get the latest git tag as the version
VERSION=$(git describe --tags --abbrev=0 2>/dev/null)
if [ -z "$VERSION" ]; then
  echo "Warning: No git tags found. Please create a tag before building. Using default version v0.1.0."
  VERSION="v0.1.0"
fi
# Remove the leading 'v' if it exists
VERSION=${VERSION#v}

# Define Prometheus version
PROMETHEUS_VERSION="2.55.1"

# Define output directories
OUTPUT_DIR="$SOURCE_DIR/../build_output"
TAR_GZ_DIR="${OUTPUT_DIR}/tar.gz"

# Cleanup previous builds
rm -rf "${OUTPUT_DIR}"
mkdir -p "${TAR_GZ_DIR}"

# Build the binary for multiple architectures
echo "Building the project for multiple architectures..."
(
    cd bff

    # Build for x86_64
    GOARCH=amd64 GOOS=linux go build -o ${OUTPUT_DIR}/crystaldba-bff-amd64 ./cmd/main.go

    # Build for ARM64
    GOARCH=arm64 GOOS=linux go build -o ${OUTPUT_DIR}/crystaldba-bff-arm64 ./cmd/main.go

    # Copy the config.json
    cp config.json ${OUTPUT_DIR}/config.json
)

# Build the UI (Solid project)
echo "Building the UI..."
(
    cd bff/solid
    npm install
    VITE_DEV_MODE=${VITE_DEV_MODE:-false} npm run build
)

TMP_DIR="/tmp"

for arch in amd64 arm64; do
    # Define paths relative to PARENT_DIR
    PARENT_DIR="${TAR_GZ_DIR}/crystaldba-${VERSION}-${arch}/crystaldba-${VERSION}"
    INSTALL_DIR="$PARENT_DIR/bin"
    WEBAPP_DIR="$PARENT_DIR/share/webapp"
    PROMETHEUS_CONFIG_DIR="$PARENT_DIR/config/prometheus"
    CRYSTALDBA_CONFIG_DIR="$PARENT_DIR/config/crystaldba"
    PROMETHEUS_INSTALL_DIR="$PARENT_DIR/prometheus"
    COLLECTOR_DIR="${PARENT_DIR}/share/collector"
    COLLECTOR_RELEASE_DIR="${TAR_GZ_DIR}/collector-${VERSION}-${arch}/collector-${VERSION}"
    COLLECTOR_API_SERVER_DIR="${PARENT_DIR}/share/collector_api_server"

    echo "Downloading Prometheus tarball for ${arch}..."
    # Prepare clean
    rm -rf $TMP_DIR/prometheus-*
    mkdir -p "${PROMETHEUS_INSTALL_DIR}"
    wget -qO- https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-${arch}.tar.gz | tar -xzf - -C $TMP_DIR/
    cp $TMP_DIR/prometheus-${PROMETHEUS_VERSION}.linux-${arch}/prometheus "${PROMETHEUS_INSTALL_DIR}/"
    cp $TMP_DIR/prometheus-${PROMETHEUS_VERSION}.linux-${arch}/promtool "${PROMETHEUS_INSTALL_DIR}/"
    mkdir -p ${PROMETHEUS_CONFIG_DIR}
    cp -r $TMP_DIR/prometheus-${PROMETHEUS_VERSION}.linux-${arch}/consoles ${PROMETHEUS_CONFIG_DIR}/
    cp -r $TMP_DIR/prometheus-${PROMETHEUS_VERSION}.linux-${arch}/console_libraries ${PROMETHEUS_CONFIG_DIR}/
    # Cleanup
    rm -rf $TMP_DIR/prometheus-*

    # Copy prometheus setup
    echo "Copying prometheus setup files..."
    mkdir -p "${PROMETHEUS_CONFIG_DIR}"
    cp prometheus/prometheus.normal.yml "${PROMETHEUS_CONFIG_DIR}/prometheus.normal.yml"
    cp prometheus/prometheus.reprocess.yml "${PROMETHEUS_CONFIG_DIR}/prometheus.reprocess.yml"
    cp prometheus/recording_rules.yml "${PROMETHEUS_CONFIG_DIR}/recording_rules.yml"

    # Copy and build the reloader service
    cd prometheus/cmd/reloader
    go build -o ${INSTALL_DIR}/prometheus-reloader
    cd -

    echo "Building collector-api-server..."
    mkdir -p "${COLLECTOR_API_SERVER_DIR}"
    cp -r collector-api/* "${COLLECTOR_API_SERVER_DIR}/"
    cd "${COLLECTOR_API_SERVER_DIR}"
    go build -o collector-api-server ./cmd/server/main.go
    cd -

    # Prepare directories for install
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${WEBAPP_DIR}"
    mkdir -p "${CRYSTALDBA_CONFIG_DIR}"
    
    cp -r ${OUTPUT_DIR}/crystaldba-bff-${arch} "${INSTALL_DIR}/crystaldba-bff"
    cp -r ${OUTPUT_DIR}/config.json "${CRYSTALDBA_CONFIG_DIR}/config.json"
    cp -r bff/solid/dist/* "${WEBAPP_DIR}"
    cp entrypoint.sh "${INSTALL_DIR}/crystaldba-entrypoint.sh"
    chmod +x "${INSTALL_DIR}/crystaldba-entrypoint.sh"

    cp prometheus/prometheus-entrypoint.sh "${PARENT_DIR}/bin/"
    cp collector-api/collector-api-entrypoint.sh "${PARENT_DIR}/bin/"
    cp bff/bff-entrypoint.sh "${PARENT_DIR}/bin/"
    
    # Copy the `install.sh` and `uninstall.sh` scripts into the root of the tarball
    cp scripts/install.sh "${PARENT_DIR}/"
    cp scripts/uninstall.sh "${PARENT_DIR}/"
    cp scripts/Makefile "${PARENT_DIR}/"

    # Build collector
    PROTOC_ARCH_SUFFIX="x86_64" # We only build for x86_64, as we're going to run it on x86_64 and use its output at build time
    echo "Building collector..."
    mkdir -p "${COLLECTOR_DIR}"
    mkdir -p "${COLLECTOR_RELEASE_DIR}"
    git clone --recurse-submodules https://github.com/crystaldb/collector.git "${COLLECTOR_DIR}"
    cd "${COLLECTOR_DIR}"
    git checkout 95ce04683c90bc99e0e9b17a2254764c30ffc289
    wget https://github.com/protocolbuffers/protobuf/releases/download/v28.2/protoc-28.2-linux-${PROTOC_ARCH_SUFFIX}.zip
    unzip protoc-28.2-linux-${PROTOC_ARCH_SUFFIX}.zip -d protoc
    make build
    
    # Move collector binaries to release directory instead of renaming in place
    mv pganalyze-collector "${COLLECTOR_RELEASE_DIR}/crystaldba-collector"
    mv pganalyze-collector-helper "${COLLECTOR_RELEASE_DIR}/crystaldba-collector-helper"
    mv pganalyze-collector-setup "${COLLECTOR_RELEASE_DIR}/crystaldba-collector-setup"
    cd -
    rm -rf "${COLLECTOR_DIR}"

    cp ./collector/collector-entrypoint.sh "${COLLECTOR_RELEASE_DIR}/"

    cp ./collector/collector-install.sh "${COLLECTOR_RELEASE_DIR}/install.sh"
    cp ./collector/collector-uninstall.sh "${COLLECTOR_RELEASE_DIR}/uninstall.sh"
done

# Function to create tar.gz package for each architecture
create_tar_gz() {
    for arch in amd64 arm64; do
        echo "Creating tar.gz packages for ${arch}..."
        # Create crystaldba package
        tar -czvf "${TAR_GZ_DIR}/crystaldba-${VERSION}-${arch}.tar.gz" -C "${TAR_GZ_DIR}/crystaldba-${VERSION}-${arch}" .
        # Create collector package
        tar -czvf "${TAR_GZ_DIR}/collector-${VERSION}-${arch}.tar.gz" -C "${TAR_GZ_DIR}/collector-${VERSION}-${arch}" .
    done
}

# Call the function to create the tar.gz
create_tar_gz

echo "Release build complete. Output located in ${OUTPUT_DIR}."
