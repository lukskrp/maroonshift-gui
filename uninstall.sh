#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# uninstall.sh -- Uninstall Maroon Shift
#
# Usage:
#   chmod +x uninstall.sh
#   sudo ./uninstall.sh   (system-wide)
#   ./uninstall.sh        (user-local)
#

set -euo pipefail

APP_CMD="maroonshift-gui"
APP_NAME="Maroon Shift"
INSTALL_DIR="/usr/local/bin"
USER_INSTALL_DIR="$HOME/.local/bin"

IS_ROOT=false
if [[ $EUID -eq 0 ]] || [[ $(id -u) -eq 0 ]]; then
    IS_ROOT=true
fi

INFO()  { printf '\033[32m[info]\033[0m  %s\n' "$*"; }
WARN()  { printf '\033[33m[warn]\033[0m  %s\n' "$*"; }
ERROR() { printf '\033[31m[error]\033[0m %s\n' "$*"; }

# ------------------------------------------------------------------
# Determine install mode
# ------------------------------------------------------------------

if ! $IS_ROOT; then
    WARN "Run with sudo to remove system-wide install."
    WARN "Uninstalling user-local install..."
    BIN_DIR="$USER_INSTALL_DIR"
    MODE="user"
else
    BIN_DIR="$INSTALL_DIR"
    MODE="system"
fi

BIN_PATH="${BIN_DIR}/${APP_CMD}"

# ------------------------------------------------------------------
# Remove binary
# ------------------------------------------------------------------

if [[ -f "$BIN_PATH" ]]; then
    rm -f "$BIN_PATH"
    INFO "Removed ${BIN_PATH}"
else
    WARN "${BIN_PATH} not found"
fi

# ------------------------------------------------------------------
# Remove desktop file
# ------------------------------------------------------------------

DESKTOP_NAME="maroonshift-gui.desktop"
DESKTOP_FILE=""

if [[ "$MODE" == "system" ]]; then
    DESKTOP_FILE="/usr/share/applications/${DESKTOP_NAME}"
else
    DESKTOP_FILE="${HOME}/.local/share/applications/${DESKTOP_NAME}"
fi

# Also check the other location in case it was installed differently
if [[ ! -f "$DESKTOP_FILE" ]]; then
    if [[ "$MODE" == "system" ]]; then
        DESKTOP_FILE="${HOME}/.local/share/applications/${DESKTOP_NAME}"
    else
        DESKTOP_FILE="/usr/share/applications/${DESKTOP_NAME}"
    fi
fi

if [[ -f "$DESKTOP_FILE" ]]; then
    rm -f "$DESKTOP_FILE"
    INFO "Removed ${DESKTOP_FILE}"
fi

# ------------------------------------------------------------------
# Clean up user-level desktop if installed system-wide
# ------------------------------------------------------------------

USER_DESKTOP="${HOME}/.local/share/applications/${DESKTOP_NAME}"
if [[ -f "$USER_DESKTOP" ]]; then
    rm -f "$USER_DESKTOP"
    INFO "Removed user desktop file ${USER_DESKTOP}"
fi

# ------------------------------------------------------------------
# Remove lock file
# ------------------------------------------------------------------

LOCK="/tmp/maroonshift-gui.lock"
if [[ -f "$LOCK" ]]; then
    rm -f "$LOCK"
    INFO "Removed lock file ${LOCK}"
fi

# ------------------------------------------------------------------
# Update desktop database
# ------------------------------------------------------------------

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    update-desktop-database "/usr/share/applications" 2>/dev/null || true
fi

echo ""
INFO "============================================"
INFO "  ${APP_NAME} uninstalled!"
INFO "============================================"
