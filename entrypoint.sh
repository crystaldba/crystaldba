#!/bin/bash

# SPDX-Identifier: Apache-2.0

# Set the base directory based on installation
PARENT_DIR="${PARENT_DIR:-/usr/local/crystaldba}"

# Set default values for PROMETHEUS_HOST and COLLECTOR_API_URL
export PROMETHEUS_HOST="${PROMETHEUS_HOST:-localhost:9090}"
export PROMETHEUS_URL="http://${PROMETHEUS_HOST}"
export COLLECTOR_API_URL="${COLLECTOR_API_URL:-http://localhost:7080}"
export CRYSTALDBA_API_KEY="${CRYSTALDBA_API_KEY:-DEFAULT-API-KEY}"

function clean_up {
    # Perform program exit housekeeping
    kill $(jobs -p)
    wait # wait for all children to exit -- this lets their logs make it out of the container environment
    exit -1
}

trap clean_up SIGHUP SIGINT SIGTERM


echo "Starting Prometheus..."
"$PARENT_DIR/bin/prometheus-entrypoint.sh" &
PROMETHEUS_PID=$!

echo "Starting Collector API Server..."
"$PARENT_DIR/bin/collector-api-entrypoint.sh" &
COLLECTOR_API_SERVER_PID=$!

echo "Starting BFF..."
"$PARENT_DIR/bin/bff-entrypoint.sh" &
BFF_PID=$!

# Wait for a process to exit
wait -n
EXITED_PID=$!
retcode=$? # store error code so we can propagate it to the container environment

if (( $EXITED_PID == $PROMETHEUS_PID ))
then
    echo "Prometheus exited with return code $retcode - killing all jobs"
elif (( $EXITED_PID == $BFF_PID ))
then
    echo "BFF exited with return code $retcode - killing all jobs"
elif (( $EXITED_PID == $COLLECTOR_API_SERVER_PID ))
then
    echo "Collector API Server exited with return code $retcode - killing all jobs"
else
    echo "An unknown background process (with PID=$EXITED_PID) exited with return code $retcode - killing all jobs"
fi

kill $(jobs -p)

wait # wait for all children to exit -- this lets their logs make it out of the container environment
echo "All processes have exited."

exit $retcode
