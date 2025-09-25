#!/bin/bash
set -e

# ==============================================================================
# "Simple Sync" Persistence Architecture
# ==============================================================================

# --- Define Core Paths ---
PERSIST_MAPPED_DIR="/.persist"
SYNC_SCRIPT="/opt/inXeption/bin/sync.sh"
SHUTDOWN_LOG="$PERSIST_MAPPED_DIR/shutdown.log"
SHUTDOWN_LOG_TMP="$PERSIST_MAPPED_DIR/shutdown.log.tmp"

# --- Shutdown Handler (TRAP) ---
# This function is registered to run when the container receives a stop signal.
function on_shutdown() {
    echo "Shutdown signal received. Syncing state to persistent storage..."
    if [ -x "$SYNC_SCRIPT" ]; then
        "$SYNC_SCRIPT" --save > "$SHUTDOWN_LOG_TMP" 2>&1
    else
        echo "⚠️ Sync script not found or not executable at $SYNC_SCRIPT." > "$SHUTDOWN_LOG_TMP"
    fi
    echo "✅ Shutdown handler completed." >> "$SHUTDOWN_LOG_TMP"

    # Atomic rename to signal completion
    mv "$SHUTDOWN_LOG_TMP" "$SHUTDOWN_LOG"
}
trap 'on_shutdown' SIGTERM SIGINT


# --- Main Startup Logic ---

# Remove any existing shutdown logs from previous run
rm -f "$SHUTDOWN_LOG" "$SHUTDOWN_LOG_TMP"

echo "Container starting up. Syncing state from persistent storage..."
if [ -x "$SYNC_SCRIPT" ]; then
    "$SYNC_SCRIPT" --load
else
    echo "Warning: Sync script not found or not executable at $SYNC_SCRIPT. Skipping sync-in."
fi
echo "✅ Persistence sync-in complete."

# ==============================================================================
# Original startup services follow
# ==============================================================================

export LOG_BASE="/host/.logs/prod/${CONTAINER_NAME}"
mkdir -p "$LOG_BASE"
echo "LOG_BASE=$LOG_BASE"

# Create system logs directory
mkdir -p "$LOG_BASE/system"
echo "Creating system logs directory at $LOG_BASE/system"

# Setup git configuration
setup_git() {
    if [ -f /host/.env ]; then
        # Source the .env file
        source /host/.env

        # Configure git with identity from .env
        git config --global user.email "${GOOGLE_EMAIL}"
        git config --global user.name "${AI_NAME}"

        # Configure git to use PAT for HTTPS
        if [ ! -z "${GITHUB_TOKEN}" ]; then
            git config --global credential.helper store
            echo "https://demeisen-avatar:${GITHUB_TOKEN}@github.com" > ~/.git-credentials
            chmod 600 ~/.git-credentials
        else
            echo "Warning: GITHUB_TOKEN not set in .env - git authentication not configured"
        fi

        # Set /host as a safe directory
        git config --global --add safe.directory /host
    else
        echo "Warning: .env file not found - git credentials not configured"
    fi
}

setup_git

# Start SSH server
service ssh start
echo "SSH server started on port 22"

# Persistent authentication is now handled by Simple Sync

# Google Cloud SDK is installed via apt and available in standard PATH

# Source and export all variables from .ports
set -a
source /host/.ports || exit 1
set +a

export PYTHONPYCACHEPREFIX=/tmp

cd /opt/inXeption/bin/services
./start_all.sh

# Set up URLs based on whether we're being accessed from L0 or L1+
if [ "$LX" = "1" ]; then
    # Use EXTERNAL_IP if provided, otherwise use localhost
    HOST="${EXTERNAL_IP:-localhost}"
    export STREAMLIT_URL="http://${HOST}:${PORT_STREAMLIT_EXTERNAL}"
    export NOVNC_URL="http://${HOST}:${PORT_NOVNC_EXTERNAL}"
    export ACCESS_URL="http://${HOST}:${PORT_HTTP_EXTERNAL}"
else
    # L1+ browser needs containerIP:INTERNAL
    CONTAINER_IP=$(hostname -i)
    export STREAMLIT_URL="http://${CONTAINER_IP}:${PORT_STREAMLIT_INTERNAL}"
    export NOVNC_URL="http://${CONTAINER_IP}:${PORT_NOVNC_INTERNAL}"
    export ACCESS_URL="http://${CONTAINER_IP}:${PORT_HTTP_INTERNAL}"
fi

# Generate index.html from template
cd /opt/inXeption/web
envsubst < static/index.html.template > /var/www/html/index.html

export PYTHONPYCACHEPREFIX=/tmp
# Suppress Firefox remote settings warnings
export MOZ_REMOTE_SETTINGS_DEVTOOLS=1

cd /opt/inXeption/lib
python http_server.py > "$LOG_BASE/system/server_logs.txt" 2>&1 &

PYTHONPATH=. STREAMLIT_SERVER_PORT=$PORT_STREAMLIT_INTERNAL  \
    python -m streamlit  run inXeption/wrapper.py > "$LOG_BASE/system/streamlit_stdout.log" &

# Play startup sound if audio is available
if [ -f /opt/inXeption/media/sounds/intro.mp3 ]; then
    echo "Playing startup sound..."
    # Try to play the sound, but with safer error handling
    # First check if we have PulseAudio connection
    if pactl info >/dev/null 2>&1; then
        # Use mpg123 which has better MP3 support
        mpg123 -q /opt/inXeption/media/sounds/intro.mp3 || echo "Audio playback failed, but continuing..."
    else
        echo "No PulseAudio connection available, skipping audio playback"
    fi
fi

echo "✨ inXeption is ready!"
echo "➡️  Open $ACCESS_URL in your browser to begin"

echo "Suggested first message:"
echo "Execute /host/wake.sh and proceed with its guidance."

# Keep the container running with proper signal handling
sleep infinity &
wait $!
