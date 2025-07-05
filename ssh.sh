#!/bin/bash
set -e

# Directory containing this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source port configuration
source "$DIR/.ports" || {
    echo "Error: Failed to load port configuration from .ports" >&2
    exit 1
}

CONTAINER_NAME=""

# Process command line arguments
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

# If no container specified, find the first running container
if [ -z "$CONTAINER_NAME" ]; then
  CONTAINER_ID=$(docker ps --format "{{.ID}}" | head -1)
  if [ -z "$CONTAINER_ID" ]; then
    echo "No running containers found."
    exit 1
  fi
  CONTAINER_NAME=$(docker inspect --format '{{.Name}}' $CONTAINER_ID | sed 's/^\///')
  echo "Found running container: $CONTAINER_NAME"
else
  # Verify the specified container exists and is running
  CONTAINER_ID=$(docker ps --filter "name=$CONTAINER_NAME" --format "{{.ID}}")
  if [ -z "$CONTAINER_ID" ]; then
    echo "Container '$CONTAINER_NAME' not found or not running."
    exit 1
  fi
fi

echo "Connecting to container $CONTAINER_NAME..."

# For macOS, we'll use a simple approach that works in most shells
# This uses /usr/bin/expect which is built into macOS
cat > /tmp/ssh_expect.exp << 'EOF'
#!/usr/bin/expect
set timeout 30
set port [lindex $argv 0]
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=yes -p $port root@localhost
expect "password:"
send "password\r"
interact
EOF

chmod +x /tmp/ssh_expect.exp

# Check if expect exists in standard macOS location
if [ -f /usr/bin/expect ]; then
    /usr/bin/expect /tmp/ssh_expect.exp $PORT_SSH_EXTERNAL
else
    echo "Warning: Expect not found at /usr/bin/expect"
    echo "Falling back to manual password entry."
    echo "When prompted, enter: password"
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=yes -p $PORT_SSH_EXTERNAL root@localhost
fi

# Clean up
rm -f /tmp/ssh_expect.exp
