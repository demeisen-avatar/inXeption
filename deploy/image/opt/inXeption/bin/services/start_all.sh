#!/bin/bash

set -e

export DISPLAY=:${DISPLAY_NUM}
./xvfb.sh
./tint2.sh
./mutter.sh
./x11vnc.sh
./novnc.sh  # Start noVNC after x11vnc is ready
