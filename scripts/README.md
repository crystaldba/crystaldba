
# Crystal DBA Scripts

This directory contains a set of scripts for managing the Crystal DBA project. Below is a summary of the provided scripts and their usage instructions.

## Scripts

1. **build.sh**: This script is used to build and release Crystal DBA.

### Usage:
```
./build.sh
```
This will build the Crystal DBA binaries for multiple architectures, prepare the web UI, include Prometheus, and generate release packages in the `build_output` directory.

2. **install.sh**: This script installs the Crystal DBA project and its dependencies, including Prometheus. It supports both system-wide and user-specific installations.

### Usage:
```
./install.sh [--system] [--install-dir <DIRECTORY>] [--config <CONFIG_FILE>]
```
- `--system`: Install system-wide under `/usr/local/crystaldba`. This flag also installs crystaldba as a service.
- `--install-dir`: Specify a custom installation directory. If not specified, `$HOME/crystaldba` is used.
- `--config`: Optionally provide an crystaldba configuration file that defines parameters for Crystal DBA.

If the input is provided via stdin, it will be validated as valid JSON before use. If invalid JSON is provided, the script will throw an error and exit.

3. **uninstall.sh**: This script uninstalls Crystal DBA from the system, removing its binaries, Prometheus, and configuration files.

### Usage:
```
./uninstall.sh [--system] [--install-dir <DIRECTORY>]
```
- `--system`: Install system-wide under `/usr/local/crystaldba`. This flag also uninstalls crystaldba service.
- `--install-dir`: Specify a custom installation directory. If not specified, `$HOME/crystaldba` is used.

4. **run.sh**: This script is used to run Crystal DBA in a Docker container. It sets up a Docker environment, runs the Crystal DBA image, and exposes Prometheus, BFF, and Collector API ports.

### Usage:
```
./run.sh [--config <CONFIG_FILE>] [--instance-id <INSTANCE_ID>] [--keep-containers] [--no-collector] [--reprocess-full-snapshots] [--reprocess-compact-snapshots]
```
- `--config`: Path to the configuration file (required unless --no-collector is set)
- `--instance-id`: Specify a unique instance ID when running multiple instances of the agent
- `--keep-containers`: Keep containers running after the script exits
- `--no-collector`: Run without the collector component
- `--reprocess-full-snapshots`: Reprocess all full snapshots from storage
- `--reprocess-compact-snapshots`: Reprocess all compact snapshots from storage

**Note**: When running with either reprocessing flag enabled, Prometheus self-monitoring and recording rules updates for newly ingested data are disabled to prevent errors during old data reprocessing. To resume normal operations, restart the server without the reprocessing flags.

The script will automatically assign ports based on your user ID and instance ID:
- Prometheus port: UID + 6000 + instance_id
- BFF WebApp port: UID + 4000 + instance_id
- Collector API port: UID + 7000 + instance_id

### Notes
- Use `sudo` for running system-wide `install.sh` and `uninstall.sh` scripts.

5. **install_release.sh**: This script automates the complete installation of Crystal DBA from released packages. It handles both the Agent and Collector installation in a single command.

### Usage:
```bash
./install_release.sh [--config <CONFIG_FILE>] [--version <VERSION>]
```
- `--config`: Path to the crystaldba.conf configuration file (required)
- `--version`: Specify Crystal DBA version to install (default: latest)

The script will:
- Download and install Crystal DBA Agent
- Download and install Crystal DBA Collector
- Set up systemd services for both components
- Verify the installation

6. **reprocess.sh**: This script manages the reprocessing of Crystal DBA snapshots. It handles stopping services, enabling reprocessing, and restarting services automatically.

### Usage:
```bash
sudo ./reprocess.sh
```

The script will:
- Stop Crystal DBA services
- Enable reprocessing flags
- Start services with reprocessing enabled

**Note**: When reprocessing is enabled, Prometheus self-monitoring and recording rules updates for newly ingested data are disabled to prevent errors during old data reprocessing. The script automatically handles returning to normal operations after reprocessing is complete.

You can monitor the reprocessing progress in the logs:
```bash
sudo journalctl -fu crystaldba
sudo journalctl -fu crystaldba-collector
```

7. **show-logs.sh**: This script provides a colorized view of the Crystal DBA service logs, combining both crystaldba and collector logs into a single stream.

### Usage:
```bash
./show-logs.sh
```

The script will:
- Display combined logs from crystaldba and crystaldba-collector services
- Color-code different components for better readability:
  - Cyan: crystaldba service logs
  - Magenta: collector service logs
  - Yellow: timestamps
- Format the output in an easy-to-read format: `[timestamp] [service] message`

Example output:
```
Jan 15 10:30:45 [crystaldba] Starting Crystal DBA service...
Jan 15 10:30:46 [collector] Initializing collector...
```
