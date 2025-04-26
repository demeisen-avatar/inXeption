#!/bin/bash

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Change to script directory
cd "$SCRIPT_DIR"

PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Source ports configuration
source $PARENT_DIR/.ports

# Set up log base directory
export LOG_BASE=$PARENT_DIR/.logs/dev
mkdir -p $LOG_BASE

# Set up log file
LOG_FILE="$LOG_BASE/dev_runner.log"

# Log a message with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

if [ "$1" != "--stop" ]; then
    # Clear the log files only when launching a new instance
    log "Erasing stale log-files"

    rm -f "$LOG_FILE"
    touch "$LOG_FILE"

    rm -f "$LOG_DIR/wrapper.log"
    rm -f "$LOG_DIR/test_app.log"

    # This flag will get set the first time a browser executes the url
    rm -f "/tmp/wrapper_started.flag" 2>/dev/null
fi

# Function to find and shutdown any running development streamlit process
# 🚨 CRITICAL: We explicitly grep for /host/inXeption/wrapper.py so that we will shutdown the process running THIS FILE.
# If we were to grep for 'streamlit' we would risk getting the `pid` of the SYSTEM streamlit,
# and nuking that destroys the conversation between the human user and the AI running in the container.
kill_streamlit_process() {
    local pid=$(ps aux | grep "[/]parent/d5/inXeption/wrapper.py" | awk '{print $2}')

    if [ -n "$pid" ]; then
        log "Stopping development Streamlit (PID: $pid)..."
        kill "$pid"
        # Wait for process to end
        while kill -0 "$pid" 2>/dev/null; do
            sleep 0.1
        done
        log "Development Streamlit stopped"
    else
        log "No development Streamlit process found"
    fi
}

# Handle command
if [ "$1" == "--stop" ]; then
    log "Starting dev_runner script (stop mode)"
    kill_streamlit_process
    exit 0
fi

log "Starting dev_runner script (launch mode)"

# Stop any existing process
kill_streamlit_process

# Start Streamlit with wrapper
log "Starting development Streamlit..."

# NOTE:
#   We need --server.headless=true else it blocks, asking us for an email
#   TODO: Maybe we can set this in host/deploy/image/root/.config/streamlit/config.toml
#   There's also `--browser.gatherUsageStats=false` but seems we don't need it

log "Running Streamlit with wrapper.py from $SCRIPT_DIR"

# Use parent directory as primary PYTHONPATH, fallback to /host
(DISPLAY=:1 PYTHONPATH=$PARENT_DIR LOG_BASE=$LOG_BASE \
    streamlit run "$SCRIPT_DIR/wrapper.py" \
    --server.port $PORT_DEV_STREAMLIT_INTERNAL \
    --server.address 0.0.0.0 \
    --server.headless=true \
    >> "$LOG_FILE" 2>&1 &)

log "Log files in project root folder in .logs/dev-latest/"

# Check the Streamlit health endpoint to confirm the service is running
log "Checking if Streamlit service is running..."
for i in {1..10}; do
  HEALTH_CHECK=$(curl -s http://localhost:$PORT_DEV_STREAMLIT_INTERNAL/_stcore/health)
  if [ "$HEALTH_CHECK" = "ok" ]; then
    log "🟢 Streamlit service is healthy and running!"
    log "AI Agent: Point your browser to http://$(hostname -i):$PORT_DEV_STREAMLIT_INTERNAL"
    log "Human (hostbox): Point your browser to http://$(hostname -i):$PORT_DEV_STREAMLIT_EXTERNAL"
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
