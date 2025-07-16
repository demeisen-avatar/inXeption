#!/bin/bash

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Change to script directory
cd "$SCRIPT_DIR"

PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Set up log base directory
export LOG_BASE=$PARENT_DIR/.logs/dev
mkdir -p $LOG_BASE

# Set up log file
LOG_FILE="$LOG_BASE/dev_runner.log"

# Set up script to log all output to file and terminal
if [ "$1" != "--stop" ]; then
    # Clean the log file when starting fresh (not in stop mode)
    rm -f "$LOG_FILE"
    touch "$LOG_FILE"

    # Redirect all stdout and stderr to both the terminal and log file
    exec > >(tee -a "$LOG_FILE") 2>&1
fi

# Log a message with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Source ports configuration
source $PARENT_DIR/.ports

# Source .env file if it exists
if [ -f "$PARENT_DIR/.env" ]; then
    log "Sourcing .env file from $PARENT_DIR/.env"
    source "$PARENT_DIR/.env"
    # Check if API key exists without ever printing its value
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        log "ANTHROPIC_API_KEY after sourcing: PRESENT (length: ${#ANTHROPIC_API_KEY})"
    else
        log "ANTHROPIC_API_KEY after sourcing: MISSING"
    fi
else
    log "WARNING: No .env file found at $PARENT_DIR/.env"
fi

if [ "$1" != "--stop" ]; then
    # This flag will get set the first time a browser executes the url
    rm -f "/tmp/wrapper_started.flag" 2>/dev/null
fi

# Function to find and shutdown any running development streamlit process
# 🚨 CRITICAL: We use port-based identification to target only the development Streamlit process.
# This avoids killing the system Streamlit which would destroy the conversation between
# the human user and the AI running in the container.
kill_streamlit_process() {
    # Get PIDs using the port and handle multiple lines safely
    local pids=($(lsof -ti :$PORT_DEV_STREAMLIT_INTERNAL 2>/dev/null | tr '\n' ' '))

    if [ ${#pids[@]} -gt 0 ]; then
        local pid_list=$(printf "%s " "${pids[@]}")
        log "Stopping development Streamlit (PIDs: $pid_list) running on port $PORT_DEV_STREAMLIT_INTERNAL..."

        # Kill each PID individually
        for pid in "${pids[@]}"; do
            kill "$pid" 2>/dev/null

            # Wait for process to end with timeout
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt 30 ]; do
                sleep 0.1
                ((count++))
            done

            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log "Process $pid did not terminate gracefully, sending SIGKILL"
                kill -9 "$pid" 2>/dev/null
            fi
        done

        log "Development Streamlit stopped"
    else
        log "No development Streamlit process found on port $PORT_DEV_STREAMLIT_INTERNAL"
    fi
}

# Handle command
if [ "$1" == "--stop" ]; then
    log "Starting dev_runner script (stop mode)"
    kill_streamlit_process
    exit 0
fi

# Check if port is already in use and identify the process using it
check_port_in_use() {
    local port=$1
    # Get PIDs using the port and handle multiple lines safely
    local pids=($(lsof -ti :"$port" 2>/dev/null | tr '\n' ' '))

    if [ ${#pids[@]} -gt 0 ]; then
        # Port is in use, return the PIDs as space-separated list
        echo "${pids[*]}"
        return 0
    else
        # Port is free
        return 1
    fi
}

# ====================================================================
# STREAMLIT CONFIGURATION NOTE:
# ====================================================================
# Streamlit has two standard ways to look for configuration files:
# 1. ~/.streamlit/config.toml (standard location)
# 2. ${CWD}/.streamlit/config.toml (project-level location)
#
# IMPORTANT: Despite what some documentation might suggest, Streamlit does NOT
# reliably use XDG-spec folders (e.g., ~/.config/streamlit/config.toml).
# Testing has confirmed that Streamlit only looks in the standard locations.
#
# For consistent behavior across both development and production environments,
# we ensure the config file is in the standard location: ~/.streamlit/config.toml
#
# The configuration settings include:
# - Dark theme setting
# - Wide mode layout
# - Other Streamlit preferences
# ====================================================================

# Setup streamlit config directory if it doesn't exist
setup_streamlit_config() {
    if [ ! -d "$SCRIPT_DIR/.streamlit" ]; then
        log "Creating streamlit config directory"
        mkdir -p "$SCRIPT_DIR/.streamlit"
        log "Streamlit config directory created at $SCRIPT_DIR/.streamlit"
    fi
}

log "Starting dev_runner script (launch mode)"

# Stop any existing process
kill_streamlit_process

# Check if our port is already in use
port_pids=$(check_port_in_use "$PORT_DEV_STREAMLIT_INTERNAL")
if [ $? -eq 0 ]; then
    log "ERROR: Port $PORT_DEV_STREAMLIT_INTERNAL is already in use by process PIDs: $port_pids"

    # Get process info for each PID
    for pid in $port_pids; do
        process_info=$(ps -p "$pid" -o pid=,user=,command= 2>/dev/null)
        if [ -n "$process_info" ]; then
            log "Process details: $process_info"
        fi
    done

    log "Use '$0 --stop' to stop the existing process(es) or manually kill with: kill $port_pids"
    exit 1
fi

# Ensure streamlit config is properly set up
setup_streamlit_config

# Start Streamlit with wrapper
log "Starting development Streamlit..."

# NOTE:
#   We need --server.headless=true else it blocks, asking us for an email
#   TODO: Maybe we can set this in host/deploy/image/root/.config/streamlit/config.toml
#   There's also `--browser.gatherUsageStats=false` but seems we don't need it

log "Running Streamlit with wrapper.py from $SCRIPT_DIR"

# Debug: Check environment right before launching streamlit
log "Environment check before streamlit launch:"
log "  ANTHROPIC_API_KEY is: ${ANTHROPIC_API_KEY:+SET (${#ANTHROPIC_API_KEY} chars)}"
log "  DISPLAY=$DISPLAY"
log "  PYTHONPATH will be: $PARENT_DIR"
log "  LOG_BASE=$LOG_BASE"
log "  Current PATH=$PATH"

# Use parent directory as primary PYTHONPATH, fallback to /host
DISPLAY=:1 PYTHONPATH=$PARENT_DIR LOG_BASE=$LOG_BASE \
    python -m streamlit run "$SCRIPT_DIR/wrapper.py" \
    --server.port $PORT_DEV_STREAMLIT_INTERNAL \
    --server.address 0.0.0.0 \
    --server.headless=true \
    >> "$LOG_FILE" 2>&1 &

log "Log files in project root folder in .logs/dev-latest/"

# Check the Streamlit health endpoint to confirm the service is running
log "Checking if Streamlit service is running..."
for i in {1..10}; do
  HEALTH_CHECK=$(curl -s http://localhost:$PORT_DEV_STREAMLIT_INTERNAL/_stcore/health)
  if [ "$HEALTH_CHECK" = "ok" ]; then
    log "🟢 Streamlit service is healthy and running!"

    # Display appropriate URLs
    # Always show both URLs since we're in L1 (containers always have LX >= 1)
    log "AI Agent: Point your browser to http://$(hostname -i):$PORT_DEV_STREAMLIT_INTERNAL"
    log "Human (hostbox): Point your browser to http://localhost:$PORT_DEV_STREAMLIT_EXTERNAL"

    log "Log files:"
    log "  Dev runner log: $LOG_FILE"
    log "  Streamlit log: /host/.logs/dev-latest/streamlit.log"
    log "To stop: $0 --stop"

    exit 0
  fi
  log "Waiting for Streamlit service to be ready (attempt $i/10)..."
  sleep 1
done

log "ERROR: Streamlit service failed to start or become healthy!"
log "NOTE: You the AI agent cannot run this, since it backgrounds a task and your bash-tool nukes its process-group upon exit"
log "  You'll have to ask your human operator to run it instead!"
