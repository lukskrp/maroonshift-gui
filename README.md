# Maroon Shift

A lightweight GTK-style GUI controller for [redshift](https://jonls.dk/redshift/),
giving you comfortable control over screen colour temperature and gamma.

## Features

- **Temperature slider** — 1000 K (warm amber) to 12 000 K (cool blue),
  midpoint at 6500 K (neutral daylight).
- **Gamma slider** — 0.2 to 2.0, in fine steps of 0.05.
- **Live colour preview** — canvas shows the exact screen colour your
  settings will produce.
- **Single-click apply** — values are sent to redshift on slider release,
  not while dragging.
- **Dark / Light theme** toggle.
- **XFCE4 panel launcher** — one click installs a panel button so you can
  adjust temperature from the desktop without opening the window.
- **Zero third-party dependencies** — pure Python 3 using only the
  standard library.

## What it does

Maroon Shift sends temperature and gamma parameters to
`/usr/bin/redshift`, which re-renders your screen's colour ramp in real
time.  This reduces blue-light exposure in the evening and adjusts the
screen to match ambient lighting — exactly what redshift was designed for.
Maroon Shift simply wraps redshift in a clean GUI with a colour-preview
canvas.

## Requirements

| Package | Purpose | Install |
|---|---|---|
| Python 3 + tkinter | Runs the GUI | `python3-tk` / `python3-tkinter` / `python3-tk` |
| redshift | Applies temperature/gamma changes | `redshift` |
| xfconf-query *(optional)* | XFCE4 panel integration | `xfce4-panel` |

## Install

### Recommended — automatic installer

```bash
chmod +x install.sh
sudo ./install.sh
```

This installs the script to `/usr/local/bin/maroonshift-gui`, creates a
desktop entry in `/usr/share/applications/`, and adds the app to your
application menu.

### User-local install (no sudo)

```bash
chmod +x install.sh
./install.sh
```

Installs to `~/.local/bin/` and `~/.local/share/applications/`.
Add `~/.local/bin` to your `PATH` if it isn't already.

### Manual (run from source)

```bash
python3 maroonshift_gui.py
```

### Uninstall

```bash
sudo ./uninstall.sh        # system-wide
./uninstall.sh             # user-local
```

## Usage

After launching, drag either slider to set your preferred values, then
release the mouse button — the new setting is applied once.  The "Reset"
button restores 6500 K and gamma 1.00 (normal screen).

The "Add to panel" button works on XFCE4: it places a launcher icon on
your panel that opens this app with a single click.

## Command-line flags

```
maroonshift-gui --version
maroonshift-gui --help
```

## Why another redshift frontend?

Existing redshift GUIs either manage a background daemon (which can conflict
with multiple control points) or lack a live colour preview.  Maroon Shift
kills any running redshift process first, so the GUI is always the sole
source of truth, and it shows you exactly what colour your settings will
produce before applying them.

## License

GNU Lesser General Public License v2.1 or later (LGPL-2.1-or-later).
See `LICENSE` for the full text.

## Contributing

Bug reports, feature requests, and pull requests are welcome.

## Screenshots

_(Add screenshots here once available)_
