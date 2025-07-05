#!/bin/bash
set -e

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

# Set up Gemini CLI persistent authentication
if [ ! -L /root/.gemini ]; then
  # Remove any existing .gemini directory
  rm -rf /root/.gemini
  # Create symbolic link to persistent storage
  ln -sf /host/.persist/.gemini /root/.gemini
  echo "Set up Gemini CLI persistent authentication"
fi

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

# Keep the container running
tail -f /dev/null
