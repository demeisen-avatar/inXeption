#!/bin/bash
# Launch kitty with proper configuration

# Ensure X resources are loaded if needed
DISPLAY=:${DISPLAY_NUM:-1} xrdb -merge ~/.Xresources 2>/dev/null || echo "Warning: Could not load X resources"

# Launch terminal with interactive shell and explicitly set starting directory to /host/
DISPLAY=:${DISPLAY_NUM:-1} kitty -e bash -c "cd /host/ && exec bash -i"
