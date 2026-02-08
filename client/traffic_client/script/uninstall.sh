#!/bin/bash
# uninstall.sh - Linux one-click uninstallation script
set -e

echo "================================================"
echo "  Traffic Client - Linux Uninstaller"
echo "================================================"

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run this script as root (sudo)."
    exit 1
fi

echo "Uninstalling Traffic Client service..."
# TODO: Implement systemd service removal logic

echo "Uninstallation complete."
