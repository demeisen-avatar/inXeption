#!/bin/bash

set -euo pipefail # A stricter, safer mode for shell scripts

# --- Core Configuration ---
# These are the fixed paths inside the container.
HOME_DIR="/root"
PERSIST_ROOT="/.persist/root"

# --- Self-Documenting Usage Function ---
usage() {
    echo "Usage: $0 --load|--save [--dry-run]"
    echo ""
    echo "This script syncs configuration files between the container's"
    echo "ephemeral home directory and the persistent storage volume."
    echo ""
    echo "Modes:"
    echo "  --load     Sync FROM persistent storage TO the home directory (on startup)."
    echo "  --save     Sync FROM the home directory TO persistent storage (on shutdown)."
    echo ""
    echo "Options:"
    echo "  --dry-run  Show what would be transferred without making any changes."
    exit 1
}

# --- Argument Parsing ---
if [[ $# -eq 0 ]]; then
    usage
fi

MODE=""
DRY_RUN_FLAG=""

for arg in "$@"; do
    case $arg in
        --load)
            MODE="load"
            shift
            ;;
        --save)
            MODE="save"
            shift
            ;;
        --dry-run)
            DRY_RUN_FLAG="--dry-run"
            shift
            ;;
        *)
            echo "Error: Unknown option: $arg"
            usage
            ;;
    esac
done

# --- Determine Sync Direction ---
SOURCE_DIR=""
DEST_DIR=""

if [[ "$MODE" == "load" ]]; then
    SOURCE_DIR="$PERSIST_ROOT"
    DEST_DIR="$HOME_DIR"
elif [[ "$MODE" == "save" ]]; then
    SOURCE_DIR="$HOME_DIR"
    DEST_DIR="$PERSIST_ROOT"
else
    echo "Error: You must specify either --load or --save."
    usage
fi

# --- The rsync Command ---
# This is where all the include/exclude logic lives.
# It is now self-contained and easy to modify.

echo "Running rsync in mode: $MODE (Dry Run: ${DRY_RUN_FLAG:-'No'})"

# The command is built in an array for safety and clarity.
rsync_cmd=(
    rsync  -a  --delete  $DRY_RUN_FLAG  \
        --include='.claude.json'  \
        --include='.claude/'  \
        --include='.claude/**'  \
        --include='.gemini/'  \
        --include='.gemini/**'  \
        --include='.firefox/'  \
        --exclude='.firefox/default/cache2/'  \
        --exclude='.firefox/default/storage/'  \
        --exclude='.firefox/default/startupCache/'  \
        --exclude='.firefox/default/safeborwsing/'  \
        --include='.firefox/**'  \
        --include='.config/ccflare/'  \
        --include='.config/ccflare/**'  \
        --include='.config/ccstatusline/'  \
        --include='.config/ccstatusline/**'  \
        --include='.config/gcloud/'  \
        --include='.config/gcloud/**'  \
        --include='.config/pip/'  \
        --include='.config/pip/**'  \
        --exclude='*'  \
    "$SOURCE_DIR/"  \
    "$DEST_DIR/"
)

# Execute the command, showing errors.
# The `set -e` will cause the script to exit if rsync fails.
"${rsync_cmd[@]}"

echo "✅ Sync completed successfully."
