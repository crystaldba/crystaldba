#!/bin/sh -e

REPO_BASE="https://github.com/crystaldba/crystaldba"

VERSION=""
VERBOSE=0
QUIET=0

log() {
    level=$1
    shift
    case "$level" in
        "DEBUG")
            if [ "$VERBOSE" -eq 1 ]; then
                if [ -n "$LOG_FILE" ]; then
                    echo "[DEBUG] $*" | tee -a "$LOG_FILE"
                else
                    echo "[DEBUG] $*"
                fi
            fi
            ;;
        "INFO")
            if [ "$QUIET" -eq 0 ]; then
                if [ -n "$LOG_FILE" ]; then
                    echo "[INFO] $*" | tee -a "$LOG_FILE"
                else
                    echo "[INFO] $*"
                fi
            fi
            ;;
        "ERROR")
            if [ -n "$LOG_FILE" ]; then
                echo "[ERROR] $*" | tee -a "$LOG_FILE" >&2
            else
                echo "[ERROR] $*" >&2
            fi
            ;;
    esac
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        --quiet)
            QUIET=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-v|--version <version>] [--verbose] [--quiet]"
            echo "If no version is specified, the latest release will be installed"
            exit 1
            ;;
    esac
done

# Only create log file if not in quiet mode
if [ "$QUIET" -eq 0 ]; then
    LOG_FILE="/tmp/crystal_client_install.log"
    echo "Installation log - $(date)" > "$LOG_FILE"
fi

log "INFO" "Starting installation..."
log "DEBUG" "Verbose mode enabled"

# Platform Detection
log "INFO" "Detecting platform..."
OS=$(uname -s)
ARCH=$(uname -m)
log "DEBUG" "Detected OS: $OS"
log "DEBUG" "Detected ARCH: $ARCH"
FILE_PREFIX="crystal-client"
EXT=".tar.gz"

if [ "$OS" = "Linux" ]; then
    if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
        FILE_SUFFIX="linux-amd64"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        FILE_SUFFIX="linux-arm64"
    else
        log "ERROR" "Unsupported Linux architecture: $ARCH"
        exit 1
    fi
elif [ "$OS" = "Darwin" ]; then
    # Check if running under Rosetta 2
    if [ "$ARCH" = "x86_64" ]; then
        if sysctl hw.optional.arm64 2> /dev/null | grep -q ': 1'; then
            log "INFO" "Detected Rosetta 2 (x86 on Apple Silicon), switching to arm64."
            ARCH="arm64"
            FILE_SUFFIX="macos_arm64"
        else
            log "INFO" "Detected Intel Mac"
            FILE_SUFFIX="macos-x86_64"
        fi
    elif [ "$ARCH" = "arm64" ]; then
        FILE_SUFFIX="macos-arm64"
    else
        log "ERROR" "Unsupported macOS architecture: $ARCH"
        exit 1
    fi
else
    log "ERROR" "Unsupported operating system: $OS"
    exit 1
fi

log "INFO" "Detected platform: $OS $ARCH"

# Fetching Release
if [ -n "$VERSION" ]; then
    log "INFO" "Installing version $VERSION..."
    RELEASE_TAG="$VERSION"
else
    log "INFO" "Fetching latest release..."
    REPO_URL="https://api.github.com/repos/${REPO_BASE#https://github.com/}/releases/latest"
    log "DEBUG" "Fetching from URL: $REPO_URL"

    RELEASE_DATA=$(curl -s "$REPO_URL")
    if ! echo "$RELEASE_DATA" | grep -q '"tag_name":'; then
        log "ERROR" "Failed to fetch release data from GitHub. Check your internet connection or GitHub API rate limits."
        exit 1
    fi

    RELEASE_TAG=$(echo "$RELEASE_DATA" | grep -o '"tag_name": "[^"]*"' | cut -d'"' -f4)

    if [ -z "$RELEASE_TAG" ]; then
        log "ERROR" "Could not determine latest release tag"
        exit 1
    fi
fi

# Construct filename with version
FILE="${FILE_PREFIX}-${FILE_SUFFIX}-${RELEASE_TAG}${EXT}"
ASSET_URL="${REPO_BASE}/releases/download/${RELEASE_TAG}/${FILE}"

log "INFO" "Using release tag: $RELEASE_TAG"
log "INFO" "Downloading from: $ASSET_URL"

# Downloading the Archive
log "INFO" "Downloading $FILE..."
DOWNLOAD_DIR="/tmp"
DOWNLOAD_PATH="$DOWNLOAD_DIR/$FILE"

if command -v curl >/dev/null 2>&1; then
    curl --retry 5 \
        --retry-delay 5 \
        --retry-max-time 60 \
        --fail \
        --proto '=https' \
        --tlsv1.2 \
        --silent \
        --show-error \
        --location \
        "$ASSET_URL" -o "$DOWNLOAD_PATH"
elif command -v wget >/dev/null 2>&1; then
    wget --tries=5 \
        --wait=5 \
        --timeout=60 \
        --no-verbose \
        --https-only \
        --secure-protocol=TLSv1_2 \
        "$ASSET_URL" -O "$DOWNLOAD_PATH"
else
    log "ERROR" "Neither curl nor wget is available."
    exit 1
fi

log "INFO" "Downloaded $FILE to $DOWNLOAD_PATH"

# Extracting the Archive
log "INFO" "Extracting $FILE..."
EXTRACT_DIR="/tmp/crystal_client"
mkdir -p "$EXTRACT_DIR"

if ! tar -xzf "$DOWNLOAD_PATH" -C "$EXTRACT_DIR"; then
    log "ERROR" "Extraction failed."
    exit 1
fi
log "INFO" "Extraction completed successfully."

# Installing the Executable
DIST_DIR="$EXTRACT_DIR/main.dist"
# Use XDG_DATA_HOME if set, otherwise default to ~/.local/lib
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local}"
INSTALL_DIR="$DATA_HOME/lib/crystaldba-client"
BIN_DIR="$DATA_HOME/bin"
INSTALL_PATH="$BIN_DIR/crystaldba"

log "INFO" "Installing executable..."
if [ ! -d "$DIST_DIR" ]; then
    log "ERROR" "Distribution directory not found at $DIST_DIR"
    exit 1
fi

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

cp -r "$DIST_DIR"/* "$INSTALL_DIR/"

# Create a symlink to the executable
ln -sf "$INSTALL_DIR/crystaldba" "$INSTALL_PATH"
chmod +x "$INSTALL_DIR/crystaldba"
log "INFO" "Executable installed to $INSTALL_PATH"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        log "INFO" "Add the following to your shell configuration file (.bashrc, .zshrc, etc):"
        log "INFO" "    export PATH=\"\$PATH:$BIN_DIR\""
        ;;
esac

# Cleanup
log "INFO" "Cleaning up..."
rm -f "$DOWNLOAD_PATH"
rm -rf "$EXTRACT_DIR"

log "INFO" "Installation complete!"
log "INFO" "You can now run Crystal Client using: crystal-client"
if [ ! -d "$BIN_DIR" ]; then
    log "INFO" "Note: You may need to restart your shell or run: export PATH=\"\$PATH:$BIN_DIR\""
fi
log "INFO" "Log file available at $LOG_FILE"
