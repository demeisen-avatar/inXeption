#!/bin/bash
echo "starting vnc $PORT_VNC_INTERNAL"

(x11vnc -display $DISPLAY \
    -forever \
    -shared \
    -wait 50 \
    -rfbport "$PORT_VNC_INTERNAL" \
    -nopw \
    2>"$LOG_BASE/system/x11vnc_stderr.log") &

x11vnc_pid=$!

# Wait for x11vnc to start
timeout=10
while [ $timeout -gt 0 ]; do
    if netstat -tuln | grep -q ":$PORT_VNC_INTERNAL "; then
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo "x11vnc failed to start, stderr output:" >&2
    cat "$LOG_BASE/system/x11vnc_stderr.log" >&2
    exit 1
fi

: > "$LOG_BASE/system/x11vnc_stderr.log"

# Monitor x11vnc process in the background
(
    while true; do
        if ! kill -0 $x11vnc_pid 2>/dev/null; then
            echo "x11vnc process crashed, restarting..." >&2
            if [ -f "$LOG_BASE/system/x11vnc_stderr.log" ]; then
                echo "x11vnc stderr output:" >&2
                cat "$LOG_BASE/system/x11vnc_stderr.log" >&2
                : > "$LOG_BASE/system/x11vnc_stderr.log"
            fi
            exec "$0"
        fi
        sleep 5
    done
) &
