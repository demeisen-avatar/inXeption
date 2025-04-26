#!/bin/bash

# Get the full path of the directory where the script is located
SCRIPT_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

# Get the base name of the directory (the last part)
DIR_NAME=$(basename "$SCRIPT_DIR")

# Get the current timestamp in the desired format
TIMESTAMP=$(date "+%Y-%m-%dT%H-%M")

# Change to the parent directory of the script location
cd "$SCRIPT_DIR/.." || exit 1

# Get optional tag from first argument
TAG="${1:+--$1}"

# Define the output zip file path in the parent directory
ZIP_NAME="/Users/pi/demeisen-backups/${DIR_NAME}--${TIMESTAMP}.${TAG}.zip"

# Create the zip file of the directory (-q for quiet)
zip -q  \
  -r "$ZIP_NAME" "$DIR_NAME"  \
  -x  \
    "$DIR_NAME/backup.sh"  \
    "$DIR_NAME/.venv/*"  \
    "$DIR_NAME/.venv/"

# Print the name of the created zip file
echo "Backup created:"  # "$(realpath "$ZIP_NAME")"
ls -lah "$ZIP_NAME"
