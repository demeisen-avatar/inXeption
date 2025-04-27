#!/bin/bash
set -e

# Directory containing this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_NAME=$(basename "$0")
USER=$(whoami)
HOST=$(hostname)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "no-git")
GIT_HASH=$(git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "no-hash")

# Generate timestamp for this run
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
mkdir -p "$DIR/.logs/runs/$TIMESTAMP"

log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') 🏠 $*" | tee -a "$DIR/.logs/runs/$TIMESTAMP/run.sh.log"
}

# Determine our level
if [ -z "$LX" ]; then
    # No LX in environment - we must be L0
    export LX=0
fi
# Announce our level with stars
STARS=$(printf '⭐️%.0s' $(seq 1 $((LX + 1))))
echo "$(date '+%Y-%m-%d %H:%M:%S') $STARS Running as L$LX"

# Change to script directory early (needed for session management)
cd "$(dirname "$0")"

# Source port configuration
source .ports || {
    echo "Error: Failed to load port configuration from .ports" >&2
    exit 1
}

# Function to check if a port is available
check_port() {
    local port=$1
    if netstat -tuln | grep -q ":${port} "; then
        echo "Error: Port ${port} is already in use" >&2
        return 1
    fi
    return 0
}

# Parse command line arguments
IMAGE_NAME=""
CONTAINER_NAME=""
EXTERNAL_IP="localhost"  # Default to localhost for local development

while [[ $# -gt 0 ]]; do
    case $1 in
        --image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --ip)
            EXTERNAL_IP="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 --image NAME --container NAME [--ip ADDRESS]"
            exit 1
            ;;
    esac
done

# Verify required arguments
if [ -z "$IMAGE_NAME" ] || [ -z "$CONTAINER_NAME" ]; then
    echo "Error: --image NAME and --container NAME are required"
    echo "Usage: $0 --image NAME --container NAME"
    exit 1
fi

# Change to script directory and source .env
cd "$(dirname "$0")"
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi
source .env

log_with_timestamp "Created /.logs/runs directory for run logs"

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY not set in .env"
    exit 1
fi

# Helper functions for ID formatting
short_id() {
    echo "$1" | cut -c1-4
}

container_name() {
    local id=$1
    local name=$2
    echo "$name ($(short_id $id)..)"
}

image_id() {
    docker inspect --format='{{.Id}}' "$1" 2>/dev/null | sed 's/sha256://'
}

# Function to check if container is running
container_is_running() {
    docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null | grep -q true
    return $?
}

# Set up logging
log_with_timestamp "=== New Run starting at $TIMESTAMP (L$LX) ==="
log_with_timestamp "$USER @ $HOST $DIR 🌿$GIT_BRANCH #$GIT_HASH"
log_with_timestamp "$SCRIPT_NAME --image $IMAGE_NAME --container $CONTAINER_NAME"
log_with_timestamp "SYSTEM: $(uname -sr), $(uname -m) architecture"
# Get memory info in a platform-independent way
if [ "$(uname)" = "Darwin" ]; then
    # macOS memory info (in GB)
    TOTAL_MEM=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)"G"}')
    AVAILABLE_MEM=$(vm_stat | awk '/Pages free/ {free=$3} /Pages speculative/ {spec=$3} /Pages inactive/ {inactive=$3} END {print int((free+spec+inactive)*4096/1024/1024/1024)"G"}' | tr -d '.')
else
    # Linux memory info
    TOTAL_MEM=$(free -h | grep Mem | awk '{print $2}')
    AVAILABLE_MEM=$(free -h | grep Mem | awk '{print $7}')
fi
log_with_timestamp "MEMORY: $TOTAL_MEM total, $AVAILABLE_MEM available"
log_with_timestamp "TIMEZONE: $(date +%Z), offset $(date +%z)"
log_with_timestamp "DOCKER: version $(docker version --format '{{.Server.Version}}')"
log_with_timestamp "---"

# Check all external ports
log_with_timestamp "Checking port availability..."
for port in $PORT_VNC_EXTERNAL $PORT_NOVNC_EXTERNAL $PORT_HTTP_EXTERNAL \
           $PORT_STREAMLIT_EXTERNAL $PORT_MATRIX_ELEMENT_EXTERNAL \
           $PORT_MATRIX_SYNAPSE_EXTERNAL; do
    check_port $port || exit 1
done
log_with_timestamp "All ports are available."

# Remove existing container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    log_with_timestamp "Removing existing $CONTAINER_NAME container..."
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1
fi

# Determine project root - if we're L1+ it should be passed in, otherwise calculate it
if [ -z "$PROJROOT" ]; then
    # We're L0 (not in container), calculate from our location
    PROJROOT="$(pwd)"
fi

# Check for audio support
AUDIO_PARAMS=""
if [ "$(uname)" = "Darwin" ]; then
    if command -v pulseaudio >/dev/null 2>&1; then
        log_with_timestamp "🔈 macOS PulseAudio detected, configuring audio routing"

        # Create ~/.config/pulse directory if it doesn't exist
        mkdir -p "$HOME/.config/pulse"

        # Restart PulseAudio with our custom configuration
        log_with_timestamp "Restarting PulseAudio with inXeption configuration"

        # Stop PulseAudio service
        brew services stop pulseaudio

        # Create symlink to our custom configuration
        ln -sf "$DIR/scripts/pulseaudio/inXeption.pa" "$HOME/.config/pulse/default.pa"

        # Start PulseAudio service
        brew services start pulseaudio

        # Set up Docker audio parameters
        AUDIO_PARAMS="-e PULSE_SERVER=docker.for.mac.localhost"
        log_with_timestamp "Mounting PulseAudio cookie for authentication"
        AUDIO_PARAMS="$AUDIO_PARAMS -v $HOME/.config/pulse:/root/.config/pulse:ro"
    else
        log_with_timestamp "🔈 ⚠️ PulseAudio not found. Install with 'brew install pulseaudio' for audio support."
    fi
else
    log_with_timestamp "🔈 ⚠️ Audio support does not yet exist for platform $(uname)."
fi

if docker info --format '{{json .Runtimes}}' | grep -q nvidia; then
    GPU_FLAG="--gpus all"
else
    GPU_FLAG=""
fi

# Prepare docker run command based on our level
if [ "$LX" = "0" ]; then
    # L0 needs port mapping to reach L1
    log_with_timestamp "Using port mapping (running from L0)"
    PARENT_DIR="$(dirname "$PROJROOT")"
    log_with_timestamp "Mapping parent directory $PARENT_DIR to /parent in container"
    log_with_timestamp "Using external IP for iframe URLs: $EXTERNAL_IP"
    CONTAINER_ID=$(docker run -d \
        ${GPU_FLAG} \
        -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
        -e PROJROOT="$PROJROOT" \
        -e LX=$((LX + 1)) \
        -e CONTAINER_NAME="$CONTAINER_NAME" \
        -e EXTERNAL_IP="$EXTERNAL_IP" \
        --hostname="L$((LX + 1))" \
        ${AUDIO_PARAMS} \
        -v "$PARENT_DIR":/parent \
        -v "$PROJROOT":/host \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -p 0.0.0.0:${PORT_VNC_EXTERNAL}:${PORT_VNC_INTERNAL} \
        -p 0.0.0.0:${PORT_STREAMLIT_EXTERNAL}:${PORT_STREAMLIT_INTERNAL} \
        -p 0.0.0.0:${PORT_NOVNC_EXTERNAL}:${PORT_NOVNC_INTERNAL} \
        -p 0.0.0.0:${PORT_HTTP_EXTERNAL}:${PORT_HTTP_INTERNAL} \
        -p 0.0.0.0:${PORT_MATRIX_ELEMENT_EXTERNAL}:${PORT_MATRIX_ELEMENT_INTERNAL} \
        -p 0.0.0.0:${PORT_MATRIX_SYNAPSE_EXTERNAL}:${PORT_MATRIX_SYNAPSE_INTERNAL} \
        -p 0.0.0.0:${PORT_DEV_STREAMLIT_EXTERNAL}:${PORT_DEV_STREAMLIT_INTERNAL} \
        --name "$CONTAINER_NAME" \
        -it "$IMAGE_NAME")
else
    log_with_timestamp "Audio support not yet supported for > L0"
    # L1+ can use direct container IPs - no port mapping needed
    log_with_timestamp "Using direct container networking (running from L$LX)"
    log_with_timestamp "Using external IP for iframe URLs: $EXTERNAL_IP"
    CONTAINER_ID=$(docker run -d \
        ${GPU_FLAG} \
        -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
        -e PROJROOT="$PROJROOT" \
        -e LX=$((LX + 1)) \
        -e CONTAINER_NAME="$CONTAINER_NAME" \
        -e EXTERNAL_IP="$EXTERNAL_IP" \
        --hostname="L$((LX + 1))" \
        -v "$PROJROOT":/host \
        -v /var/run/docker.sock:/var/run/docker.sock \
        --name "$CONTAINER_NAME" \
        -it "$IMAGE_NAME")
fi

if [ -z "$CONTAINER_ID" ]; then
    log_with_timestamp "Error: Failed to start container."
    exit 1
fi

# Get image ID for nice display
IMAGE_ID=$(image_id "$IMAGE_NAME")

log_with_timestamp "Container $(container_name "$CONTAINER_ID" "$CONTAINER_NAME") started from image $IMAGE_NAME ($(short_id "$IMAGE_ID")..)"

# Wait until the container is fully running
log_with_timestamp "Waiting for container to reach running state..."
until container_is_running; do
    sleep 1
done
log_with_timestamp "Container is now running."

# Log container details
log_with_timestamp "CONTAINER: Built from $(docker inspect --format '{{.Config.Image}}' "$CONTAINER_ID")"
log_with_timestamp "NETWORK: $(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CONTAINER_ID")"

# Start log streaming in background with session logging
docker logs -f "$CONTAINER_ID" | while read -r line; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') 🐋 $line" | tee -a "$DIR/.logs/runs/$TIMESTAMP/run.sh.log"
done &
LOG_PID=$!

# Initialize signal handling
SIGNAL_RECEIVED=0
CLEANUP_DONE=0

# Function to stop container and clean up processes
stop_container_and_cleanup() {
    log_with_timestamp "Stopping container $(container_name "$CONTAINER_ID" "$CONTAINER_NAME")..."
    result=$(docker stop "$CONTAINER_ID" 2>&1)
    if [ "$result" = "$CONTAINER_ID" ]; then
        log_with_timestamp "✅ Stopped"
    else
        log_with_timestamp "⚠️  Unexpected output: $result"
    fi

    log_with_timestamp "Cleaning up background processes..."
    # Kill processes if they exist
    [ -n "$LOG_PID" ] && kill $LOG_PID 2>/dev/null
    if [ -n "$WEBAI_PID" ]; then
        kill $WEBAI_PID 2>/dev/null
        sleep 1
        kill -9 $WEBAI_PID 2>/dev/null
    fi

    log_with_timestamp "Shutdown complete."
}

# Normal exit handler
on_normal_exit() {
    if [ "$CLEANUP_DONE" -eq 1 ]; then
        return
    fi
    CLEANUP_DONE=1

    if [ "$LX" -eq 0 ]; then
        # L0: Stop container on normal exit
        log_with_timestamp "Shutting down..."
        stop_container_and_cleanup
    else
        # L1+: Keep container running on normal exit
        # Get container IP and full container ID
        CONTAINER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CONTAINER_ID")
        FULL_CONTAINER_ID=$(docker inspect -f '{{.Id}}' "$CONTAINER_ID")
        SESSION_LOG_PATH="$DIR/.logs/runs/$TIMESTAMP/run.sh.log"

        log_with_timestamp "L$((LX+1)) container successfully started!"
        log_with_timestamp "CONTAINER ID: $FULL_CONTAINER_ID"
        log_with_timestamp "LOG FILE: $SESSION_LOG_PATH"

        log_with_timestamp "L$((LX+1)) container access points:"
        log_with_timestamp "- Combined interface: http://${CONTAINER_IP}:${PORT_HTTP_INTERNAL}"
        log_with_timestamp "- Streamlit interface: http://${CONTAINER_IP}:${PORT_STREAMLIT_INTERNAL}"
        log_with_timestamp "- Desktop view: http://${CONTAINER_IP}:${PORT_NOVNC_INTERNAL}/vnc.html"
        log_with_timestamp "- Direct VNC: vnc://${CONTAINER_IP}:${PORT_VNC_INTERNAL}"
        log_with_timestamp "- Matrix Element: http://${CONTAINER_IP}:${PORT_MATRIX_ELEMENT_INTERNAL}"
        log_with_timestamp "- Matrix Synapse: http://${CONTAINER_IP}:${PORT_MATRIX_SYNAPSE_INTERNAL}"

        # Additional useful information
        log_with_timestamp "To check container status: docker inspect $CONTAINER_NAME"
        log_with_timestamp "To stop container: docker stop $CONTAINER_NAME"

        # Clean up log streaming but leave container running
        [ -n "$LOG_PID" ] && kill $LOG_PID 2>/dev/null

        log_with_timestamp "Detached. Container continues running."
    fi
}

# Interrupt handler (INT/TERM)
on_interrupt() {
    if [ "$CLEANUP_DONE" -eq 1 ]; then
        return
    fi
    CLEANUP_DONE=1

    log_with_timestamp "Received interrupt or termination signal."
    # Always stop container for interrupts, regardless of L-level
    log_with_timestamp "Shutting down due to interrupt..."
    stop_container_and_cleanup
}

# Set different handlers for different signals
trap 'on_normal_exit' EXIT
trap 'SIGNAL_RECEIVED=1; on_interrupt' INT TERM

log_with_timestamp "Container started. Access points:"
log_with_timestamp "- Combined interface: http://localhost:${PORT_HTTP_EXTERNAL}"
log_with_timestamp "- Streamlit interface: http://localhost:${PORT_STREAMLIT_EXTERNAL}"
log_with_timestamp "- Desktop view: http://localhost:${PORT_NOVNC_EXTERNAL}/vnc.html"
log_with_timestamp "- Direct VNC: vnc://localhost:${PORT_VNC_EXTERNAL}"
log_with_timestamp "- Matrix Element: http://localhost:${PORT_MATRIX_ELEMENT_EXTERNAL}"
log_with_timestamp "- Matrix Synapse: http://localhost:${PORT_MATRIX_SYNAPSE_EXTERNAL}"

# Exit immediately if running from L1+
if [ "$LX" -gt 0 ]; then
    log_with_timestamp "Container ready. Exiting non-blocking mode (L$LX)."
    exit 0
fi

# Monitor loop (only for L0)
while container_is_running; do
    sleep 1
done

# Only show error if we didn't receive SIGINT/SIGTERM
if [ "${SIGNAL_RECEIVED:-0}" != "1" ]; then
    log_with_timestamp "Container stopped unexpectedly."
    exit 1
fi
