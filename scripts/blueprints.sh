#!/bin/bash
# Wrapper script for blueprint.py that scans a directory for blueprints

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/blueprint.py"
PROJROOT="$SCRIPT_DIR/.."

# Check if python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Could not find blueprint.py in $SCRIPT_DIR"
    exit 1
fi

# Make sure blueprint.py is executable
chmod +x "$PYTHON_SCRIPT"

# Default values
TARGET_DIR="$PROJROOT"
CHECK_MODE=""

# Parse arguments
for arg in "$@"; do
    if [ "$arg" == "--check" ]; then
        CHECK_MODE="--check"
    elif [ ! "$arg" == "--"* ]; then
        # If not starting with --, treat as target directory
        TARGET_DIR="$arg"
    fi
done

# Run the Python script with appropriate arguments
# Run the Python script with appropriate arguments
"$PYTHON_SCRIPT" $CHECK_MODE "$TARGET_DIR"
exit $?
