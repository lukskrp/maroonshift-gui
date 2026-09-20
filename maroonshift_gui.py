#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# maroonshift-gui -- A small GUI controller for redshift.
#
# Controls colour temperature and gamma, and can add itself to the XFCE4
# panel as a Launcher (tool icon) button.
#
# Copyright 2025 Maroon Shift Contributors
#

import argparse
import configparser
import math
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

__version__ = "1.0.0"

APP_NAME = "Maroon Shift"

DEFAULT_TEMP = 6500
DEFAULT_GAMMA = 1.0

# Default redshift path; we also search PATH for it so the script works
# regardless of where the package was installed by the distro.
REDSHIFT_DEFAULT = "/usr/bin/redshift"


# ---------------------------------------------------------------------------
# Theme definitions (light / dark)
# ---------------------------------------------------------------------------

THEMES = {
    "light": {
        "bg": "#f5f5f5",
        "fg": "#1c1c1c",
        "widget": "#ffffff",
        "widget_fg": "#1c1c1c",
        "accent": "#4a90d9",
        "accent_fg": "#ffffff",
        "danger": "#d9534f",
        "danger_fg": "#ffffff",
        "select": "#e0e0e0",
        "trough": "#d0d0d0",
    },
    "dark": {
        "bg": "#232323",
        "fg": "#e8e8e8",
        "widget": "#2d2d2d",
        "widget_fg": "#e8e8e8",
        "accent": "#4a90d9",
        "accent_fg": "#ffffff",
        "danger": "#b0483f",
        "danger_fg": "#ffffff",
        "select": "#3a3a3a",
        "trough": "#4a4a4a",
    },
}

BG_MODE = "dark"  # default; toggled by the theme button


# ---------------------------------------------------------------------------
# redshift helpers
# ---------------------------------------------------------------------------

def _find_redshift():
    """Locate the redshift binary on the system.

    Checks the compiled-in default path first, then searches $PATH.
    Returns the full path or None if not found.
    """
    if os.path.isfile(REDSHIFT_DEFAULT) and os.access(REDSHIFT_DEFAULT, os.X_OK):
        return REDSHIFT_DEFAULT
    try:
        result = subprocess.run(
            ["which", "redshift"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return None


REDSHIFT = _find_redshift()


def _kill_redshift_daemon():
    """Stop any running redshift/redshift-gtk so the GUI owns the screen."""
    for pattern in ("redshift-gtk", "redshift -v"):
        subprocess.run(["pkill", "-f", pattern], stderr=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL)


def redshift(cmd_args):
    """Run redshift with the given arguments, returning its return code."""
    if REDSHIFT is None:
        return -1
    try:
        proc = subprocess.run(
            [REDSHIFT] + cmd_args,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return proc.returncode
    except FileNotFoundError:
        return -1


def apply(temp, gamma):
    """Apply a combined temperature + gamma adjustment.

    ``-P`` resets the existing gamma ramps first, so every adjustment is
    absolute rather than compounding on the previous one.  Without it,
    repeated one-shot calls progressively darken the screen until it
    goes pitch black (which is what the reset button had to undo).

    Note: gamma is always sent together with a temperature because
    ``redshift -g`` on its own starts its continuous daemon loop.
    """
    t = int(temp) if temp is not None else 6500
    if gamma is not None:
        g = f"{gamma:.2f}:{gamma:.2f}:{gamma:.2f}"
        return redshift(["-P", "-O", str(t), "-g", g])
    return redshift(["-P", "-O", str(t)])


def reset_screen():
    """Reset the screen to normal (clear gamma ramps)."""
    return redshift(["-x"])


# ---------------------------------------------------------------------------
# settings persistence
# ---------------------------------------------------------------------------

def _config_path():
    """Return the path to the user settings INI file."""
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "maroonshift-gui" / "config.ini"


def load_settings():
    """Return (temperature, gamma) from disk, falling back to defaults."""
    cfg = configparser.ConfigParser()
    try:
        cfg.read(_config_path())
        temp = int(cfg.get("Settings", "temperature", fallback=str(DEFAULT_TEMP)))
        gamma = float(cfg.get("Settings", "gamma", fallback=str(DEFAULT_GAMMA)))
    except (OSError, ValueError, configparser.Error):
        return DEFAULT_TEMP, DEFAULT_GAMMA
    temp = _clamp(temp, 1000, 12000)
    gamma = round(_clamp(gamma, 0.2, 2.0), 2)
    return temp, gamma


def save_settings(temp, gamma):
    """Persist temperature and gamma to disk, silently ignoring errors."""
    try:
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        cfg = configparser.ConfigParser()
        cfg["Settings"] = {
            "temperature": str(int(temp)),
            "gamma": f"{float(gamma):.2f}",
        }
        with open(path, "w") as fh:
            cfg.write(fh)
    except (OSError, ValueError):
        pass


# ---------------------------------------------------------------------------
# colour preview helper
# ---------------------------------------------------------------------------

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def kelvin_to_rgb(k):
    """Approximate RGB colour for a black-body temperature (Tanner Helland)."""
    k = k / 100.0
    if k <= 66:
        r = 255
        g = 99.4708025861 * math.log(k) - 161.1195681661
        b = 0 if k <= 19 else 138.5177312231 * math.log(k - 10) - 305.0447927307
    else:
        r = 329.698727446 * (k - 60) ** -0.1332047592
        g = 288.1221695283 * (k - 60) ** -0.0755148492
        b = 255
    return (_clamp(r, 0, 255), _clamp(g, 0, 255), _clamp(b, 0, 255))


# ---------------------------------------------------------------------------
# panel installation
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
DESKTOP_NAME = "maroonshift-gui.desktop"
DESKTOP_USER = Path.home() / ".local" / "share" / "applications" / DESKTOP_NAME
DESKTOP_SYSTEM = Path("/usr/share/applications") / DESKTOP_NAME
INSTALL_PATH = Path("/usr/local/bin/maroonshift-gui")


def _desktop_file(exec_path=None):
    """Return the contents of a .desktop file.

    ``exec_path`` is the path to run; if not given the installed binary
    path is used.
    """
    exe = exec_path or str(INSTALL_PATH)
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Version=1.0\n"
        f"Name={APP_NAME}\n"
        "Comment=Redshift temperature and gamma controller\n"
        f"Exec={exe}\n"
        "Icon=redshift\n"
        "Terminal=false\n"
        "Categories=Utility;\n"
    )


def _next_plugin_id(panel):
    """Return the next unused plugin id greater than every id on the panel."""
    max_id = 22
    ids = _panel_plugin_ids(panel)
    if ids:
        max_id = max(ids)
    candidate = max_id + 1
    while candidate in ids:
        candidate += 1
    return candidate


def _panel_plugin_ids(panel):
    try:
        out = subprocess.check_output(
            ["xfconf-query", "-c", "xfce4-panel", "-p",
             f"/panels/panel-{panel}/plugin-ids", "-lv"],
            stderr=subprocess.DEVNULL,
        ).decode()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    m = re.search(r"\[([^\]]*)\]", out)
    if not m:
        return []
    return [int(x) for x in m.group(1).split(",") if x.strip()]


def _panel_numbers():
    """Return the numbers of every panel configured in xfce4-panel."""
    try:
        out = subprocess.check_output(
            ["xfconf-query", "-c", "xfce4-panel", "-l"],
            stderr=subprocess.DEVNULL,
        ).decode()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return sorted({
        int(m) for m in re.findall(r"/panels/panel-(\d+)/plugin-ids", out)
    })


def add_to_panel(panel=None, status_cb=None):
    """Add a Launcher plugin pointing at this app to the given panel.

    If ``panel`` is None the first configured panel is used, so the launcher
    always lands on a panel that actually exists.
    """
    def _status(msg):
        if status_cb:
            status_cb(msg)

    try:
        subprocess.check_call(
            ["which", "xfconf-query"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        _status("xfconf-query not found")
        return False

    if panel is None:
        panels = _panel_numbers()
        panel = panels[0] if panels else 1

    # Try the installed path first, fall back to running the Python file
    # directly from its source location (useful during development).
    if INSTALL_PATH.exists():
        exec_path = str(INSTALL_PATH)
    else:
        exec_path = f"{sys.executable} {APP_DIR / Path(__file__).name}"

    DESKTOP_USER.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_USER.write_text(_desktop_file(exec_path))
    _status("Wrote desktop launcher")

    plugin_id = _next_plugin_id(panel)
    xc = ["xfconf-query", "-c", "xfce4-panel"]

    subprocess.run(xc + ["--create", "-t", "string", "--set", "launcher",
                         "-p", f"/plugins/plugin-{plugin_id}"],
                   check=True, stderr=subprocess.DEVNULL)
    subprocess.run(xc + ["--create", "-t", "string", "--set", DESKTOP_NAME,
                         "-p", f"/plugins/plugin-{plugin_id}/items/0"],
                   check=True, stderr=subprocess.DEVNULL)

    # Rebuild the plugin-ids array including the new id (xfconf-query cannot
    # append to an array, so the whole list must be written at once).
    ids = _panel_plugin_ids(panel)
    cmd = xc + ["-p", f"/panels/panel-{panel}/plugin-ids"]
    for i in ids + [plugin_id]:
        cmd += ["-t", "int", "-s", str(i)]
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
    _status(f"Appended launcher plugin-{plugin_id} to panel-{panel}")

    os.environ.setdefault("DISPLAY", ":0.0")
    subprocess.run(["xfce4-panel", "-r"], stderr=subprocess.DEVNULL)
    _status("Panel reloaded")
    return True


# ---------------------------------------------------------------------------
# lock file
# ---------------------------------------------------------------------------

_LOCK = Path("/tmp/maroonshift-gui.lock")


def _acquire_lock():
    """Create a pid lockfile; return True if acquired, False if already running."""
    try:
        if _LOCK.exists():
            pid = int(_LOCK.read_text().strip())
            if Path(f"/proc/{pid}").exists():
                return False
            _LOCK.unlink(missing_ok=True)
        _LOCK.write_text(str(os.getpid()))
        return True
    except (OSError, ValueError):
        return True


# ---------------------------------------------------------------------------
# application
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="maroonshift-gui",
        description="Maroon Shift – A small GUI controller for redshift.",
    )
    parser.add_argument(
        "-V", "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()

    if not _acquire_lock():
        print("Maroon Shift is already running.", file=sys.stderr)
        return

    if REDSHIFT is None:
        print(
            "redshift not found. Please install it:\n"
            "  Debian/Ubuntu:  sudo apt install redshift\n"
            "  Fedora:         sudo dnf install redshift\n"
            "  Arch:           sudo pacman -S redshift",
            file=sys.stderr,
        )
        return

    _kill_redshift_daemon()

    root = tk.Tk()
    root.title(APP_NAME)
    root.resizable(False, False)

    start_temp, start_gamma = load_settings()
    temp_var = tk.IntVar(value=start_temp)
    gamma_var = tk.DoubleVar(value=start_gamma)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # ---- widgets ----
    title = tk.Label(root, text=APP_NAME)
    preview = tk.Canvas(root, height=26, highlightthickness=1, bd=0)
    temp_label = tk.Label(root, text="Temperature (K):")
    temp_val = tk.Label(root, text="6500", width=5, anchor="e")
    gamma_label = tk.Label(root, text="Gamma:")
    gamma_val = tk.Label(root, text="1.00", width=5, anchor="e")

    # Temperature range is centred on the neutral 6500K so the slider
    # midpoint is neutral: left = warmer/redder, right = cooler/bluer.
    temp_scale = tk.Scale(
        root, orient="horizontal", from_=1000, to=12000,
        resolution=100, variable=temp_var, showvalue=False,
    )
    gamma_scale = tk.Scale(
        root, orient="horizontal", from_=0.2, to=2.0,
        resolution=0.05, variable=gamma_var, showvalue=False,
    )

    def _preview_color():
        r, g, b = kelvin_to_rgb(temp_var.get())
        gamma = gamma_var.get()
        return "#%02x%02x%02x" % (
            int(_clamp(r * gamma, 0, 255)),
            int(_clamp(g * gamma, 0, 255)),
            int(_clamp(b * gamma, 0, 255)),
        )

    def _update_preview():
        temp = temp_var.get()
        gamma = round(gamma_var.get(), 2)
        temp_val.config(text=str(temp))
        gamma_val.config(text=f"{gamma:.2f}")
        preview.config(bg=_preview_color())

    # Live feedback while dragging: labels + preview only.  The actual
    # screen adjustment happens once, on release, so every application
    # is deliberate and unambiguous.
    def _on_change(_=None):
        _update_preview()

    def _do_apply():
        _update_preview()
        temp = temp_var.get()
        gamma = round(gamma_var.get(), 2)
        ok = apply(temp, gamma)
        if ok == 0:
            save_settings(temp, gamma)
            status.config(text=f"Applied: redshift -P -O {temp} -g {gamma:.2f}")
        else:
            status.config(text="Apply failed (is redshift available?)")

    def _apply_on_release(_=None):
        _do_apply()

    temp_scale.configure(command=_on_change)
    gamma_scale.configure(command=_on_change)
    temp_scale.bind("<ButtonRelease-1>", _apply_on_release)
    gamma_scale.bind("<ButtonRelease-1>", _apply_on_release)

    def _reset():
        reset_screen()
        temp_var.set(DEFAULT_TEMP)
        gamma_var.set(DEFAULT_GAMMA)
        save_settings(DEFAULT_TEMP, DEFAULT_GAMMA)
        _update_preview()
        status.config(
            text="Screen reset to normal (6500K, gamma 1.00)"
        )

    def _add_to_panel_cb():
        status.config(text="Installing...")
        ok = add_to_panel(status_cb=lambda msg: status.config(text=msg))
        if not ok:
            status.config(text="Failed to add to panel")

    reset_btn = tk.Button(root, text="Reset", command=_reset)
    theme_btn = tk.Button(
        root, text="Dark", command=lambda: _toggle_theme(root)
    )
    add_btn = tk.Button(root, text="Add to panel", command=_add_to_panel_cb)
    status = tk.Label(
        root,
        text="Ready — drag a slider, release to apply",
        anchor="w",
    )

    # ---- layout ----
    title.grid(row=0, column=0, columnspan=3, pady=(10, 4))
    preview.grid(
        row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6),
    )
    temp_label.grid(row=2, column=0, sticky="w", padx=(10, 4))
    temp_scale.grid(
        row=3, column=0, columnspan=2, sticky="ew", padx=10,
    )
    temp_val.grid(row=3, column=2, padx=(0, 10))
    gamma_label.grid(row=4, column=0, sticky="w", padx=(10, 4))
    gamma_scale.grid(
        row=5, column=0, columnspan=2, sticky="ew", padx=10,
    )
    gamma_val.grid(row=5, column=2, padx=(0, 10))
    reset_btn.grid(
        row=6, column=0, padx=(10, 4), pady=(10, 4), sticky="ew",
    )
    theme_btn.grid(
        row=6, column=1, padx=4, pady=(10, 4), sticky="ew",
    )
    add_btn.grid(
        row=6, column=2, padx=(4, 10), pady=(10, 4), sticky="ew",
    )
    status.grid(
        row=7, column=0, columnspan=3, sticky="ew",
        padx=10, pady=(0, 10),
    )

    root.columnconfigure(1, weight=1)
    _update_preview()

    # ---- callbacks ----
    def _toggle_theme(r):
        global BG_MODE
        BG_MODE = "light" if BG_MODE == "dark" else "dark"
        _apply_theme(r)
        theme_btn.config(text="Dark" if BG_MODE == "light" else "Light")

    # ---- theme ----
    def _apply_theme(r):
        t = THEMES[BG_MODE]
        r.configure(bg=t["bg"])
        for w in (title, temp_label, temp_val, gamma_label, gamma_val, status):
            w.configure(bg=t["bg"], fg=t["fg"])
        preview.configure(
            bg=_preview_color(), highlightbackground=t["select"],
        )
        for s in (temp_scale, gamma_scale):
            s.configure(
                bg=t["bg"], fg=t["fg"],
                highlightbackground=t["bg"],
                activebackground=t["select"],
                troughcolor=t["trough"],
            )
        for b in (reset_btn, add_btn):
            b.configure(
                bg=t["widget"], fg=t["widget_fg"],
                activebackground=t["select"],
                activeforeground=t["fg"],
                relief="flat", bd=1,
            )
        theme_btn.configure(
            bg=t["accent"], fg=t["accent_fg"],
            activebackground=t["accent"],
            activeforeground=t["accent_fg"],
            relief="flat", bd=1,
        )

    _apply_theme(root)
    _do_apply()  # restore last applied settings
    root.mainloop()
    _LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
