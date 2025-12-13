#!/bin/bash
# Video Download Server - Menu Bar Launcher
# Double-click this file to start the menu bar app

# Get the directory where this script is located
cd "$(dirname "$0")"

# Activate virtual environment and start menu bar app
source venv/bin/activate
python menubar_app.py

