#!/bin/bash
# Launcher for Video Server Menu Bar App

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
./venv/bin/python menubar_app.py
