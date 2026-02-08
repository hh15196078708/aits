#!/bin/bash
# install.sh - Linux one-click installation script
set -e

echo "================================================"
echo "  Traffic Client - Linux Installer"
echo "================================================"

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run this script as root (sudo)."
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install dependencies
echo "Installing dependencies..."
pip3 install -r "$SCRIPT_DIR/../requirements.txt"

echo "Installation complete."
