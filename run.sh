#!/bin/bash
# Uruchamia oglądarkę mebli z venv projektu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
export QT_OPENGL=desktop
export __GLX_VENDOR_LIBRARY_NAME=nvidia
exec "$DIR/venv/bin/python" "$DIR/viewer.py" "$@"
