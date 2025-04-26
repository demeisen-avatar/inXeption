#!/bin/bash
echo "starting noVNC"

# Start noVNC with explicit websocket settings
/opt/noVNC/utils/novnc_proxy \
    --vnc localhost:$PORT_VNC_INTERNAL \
    --listen $PORT_NOVNC_INTERNAL \
    --web /opt/noVNC \
    > "$LOG_BASE/system/novnc.log" 2>&1 &

# Wait for noVNC to start
timeout=10
while [ $timeout -gt 0 ]; do
    if netstat -tuln | grep -q ":$PORT_NOVNC_INTERNAL "; then
        break
    fi
    sleep 1
    ((timeout--))
done

echo "noVNC started successfully"
