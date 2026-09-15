#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# install.sh -- Install Maroon Shift system-wide
#
# Usage:
#   chmod +x install.sh
#   sudo ./install.sh
#
# If run without sudo the installer only copies the script to ~/.local/bin
# and does not create a system-wide .desktop entry.
#

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="${SCRIPT_DIR}/maroonshift_gui.py"

APP_NAME="Maroon Shift"
APP_CMD="maroonshift-gui"
INSTALL_DIR="/usr/local/bin"
USER_INSTALL_DIR="$HOME/.local/bin"

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_info()  { printf '\033[32m[info]\033[0m  %s\n' "$*"; }
_warn()  { printf '\033[33m[warn]\033[0m  %s\n' "$*"; }
_err()   { printf '\033[31m[error]\033[0m %s\n' "$*"; }

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        _err "Missing required command: $1"
        return 1
    fi
}

# ------------------------------------------------------------------
# Pre-flight checks
# ------------------------------------------------------------------

if [[ ! -f "$SOURCE_FILE" ]]; then
    _err "Cannot find ${APP_CMD}.py in ${SCRIPT_DIR}"
    exit 1
fi

check_cmd python3 || exit 1

# ------------------------------------------------------------------
# Determine install mode
# ------------------------------------------------------------------

IS_ROOT=false
if [[ $EUID -eq 0 ]] || [[ $(id -u) -eq 0 ]]; then
    IS_ROOT=true
fi

INSTALL_BIN_DIR="$INSTALL_DIR"
INSTALL_MODE="system"

if ! $IS_ROOT; then
    _warn "Run with sudo for system-wide install."
    _warn "Falling back to user-local install (~/.local/bin)..."
    INSTALL_BIN_DIR="$USER_INSTALL_DIR"
    INSTALL_MODE="user"
fi

mkdir -p "$INSTALL_BIN_DIR"

# ------------------------------------------------------------------
# Install the script
# ------------------------------------------------------------------

DEST="${INSTALL_BIN_DIR}/${APP_CMD}"

if [[ -f "$DEST" ]]; then
    _warn "Already installed at ${DEST}"
    read -rp "Overwrite? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy] ]]; then
        _info "Aborted."
        exit 0
    fi
fi

cp "$SOURCE_FILE" "$DEST"
chmod +x "$DEST"
_info "Installed to ${DEST}"

# ------------------------------------------------------------------
# Install desktop file
# ------------------------------------------------------------------

DESKTOP_NAME="maroonshift-gui.desktop"

if [[ "$INSTALL_MODE" == "system" ]]; then
    DESKTOP_DIR="/usr/share/applications"
    mkdir -p "$DESKTOP_DIR"
    DESKTOP_FILE="${DESKTOP_DIR}/${DESKTOP_NAME}"
else
    DESKTOP_DIR="${HOME}/.local/share/applications"
    mkdir -p "$DESKTOP_DIR"
    DESKTOP_FILE="${DESKTOP_DIR}/${DESKTOP_NAME}"
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=${APP_NAME}
Comment=Redshift temperature and gamma controller
Exec=${DEST}
Icon=redshift
Terminal=false
Categories=Utility;
EOF

_info "Desktop file written to ${DESKTOP_FILE}"

# ------------------------------------------------------------------
# Desktop database update
# ------------------------------------------------------------------

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    gtk-update-icon-cache "/usr/share/icons/hicolor" 2>/dev/null || true
fi

# ------------------------------------------------------------------
# Post-install message
# ------------------------------------------------------------------

echo ""
_info "============================================"
_info "  ${APP_NAME} installed successfully!"
_info "============================================"
echo ""
_info "You can now:"
if [[ "$INSTALL_MODE" == "system" ]]; then
    info "  Run: ${APP_CMD}"
else
    info "  Run: ${APP_CMD}  (add ${USER_INSTALL_DIR} to your PATH)"
fi
_info "  Search \"${APP_NAME}\" in your application menu"
echo ""
_info "Prerequisites (if not already installed):"
_info "  - Python 3 (with tkinter): sudo apt install python3 python3-tk"
_info "  - redshift:                sudo apt install redshift"
if command -v xfconf-query &>/dev/null; then
    info "  - XFCE4 panel integration is available"
else
    warn "  - xfconf-query not found (XFCE4 panel feature unavailable)"
fi
echo ""
