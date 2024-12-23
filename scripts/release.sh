#!/bin/bash

# SPDX-Identifier: Apache-2.0

set -e

# Get the directory of the currently executing script
SOURCE_DIR=$(dirname "$(readlink -f "$0")")

cd $SOURCE_DIR/..

docker build -f Dockerfile . --target release --tag crystaldbarelease
docker run --rm -v ./release_output:/release_output crystaldbarelease /bin/bash -c "cp /home/crystaldba/release_output/* /release_output"

echo "Release artifacts are available in the release_output directory"
