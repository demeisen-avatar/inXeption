#!/bin/bash
set -e

# Directory containing this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source port configuration from the .ports file in the same directory
source "$DIR/.ports" || {
    echo "Error: Failed to load port configuration from .ports" >&2
    exit 1
}

CONTAINER_NAME=""

# Process command line arguments to optionally specify a container
while [[ $# -gt 0 ]]; do
  case $1 in
    --container)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--container NAME]"
      exit 1
      ;;
  esac
done

# If no container name was specified, find the first running container
if [ -z "$CONTAINER_NAME" ]; then
  CONTAINER_ID=$(docker ps --format "{{.ID}}" | head -1)
  if [ -z "$CONTAINER_ID" ]; then
    echo "No running containers found."
    exit 1
  fi
  # Get the container's name from its ID
  CONTAINER_NAME=$(docker inspect --format '{{.Name}}' $CONTAINER_ID | sed 's/^\///')
  echo "Found running container: $CONTAINER_NAME"
else
  # If a container name was given, verify it exists and is running
  CONTAINER_ID=$(docker ps --filter "name=$CONTAINER_NAME" --format "{{.ID}}")
  if [ -z "$CONTAINER_ID" ]; then
    echo "Container '$CONTAINER_NAME' not found or not running."
    exit 1
  fi
fi

echo "Connecting to container $CONTAINER_NAME..."
echo ""
echo "When prompted, enter the password: password"
echo ""

# Connect directly using SSH and prompt for the password manually.
# This avoids using 'expect' and ensures the terminal environment is clean.
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=yes -p $PORT_SSH_EXTERNAL root@localhost
