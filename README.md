# LinxPad

A macOS-style fullscreen application launcher for Linux, supporting both X11 and Wayland sessions.

![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/andrianos)
---

## Features

- Full-screen grid of application icons, auto-populated from `.desktop` files
- Folder grouping with drag-and-drop reordering
- Multi-page navigation with page indicator dots
- Integrated search — apps, files, and web
- Settings panel for grid layout, font size, transparency, and launch mode
- Live reload — detects new/removed applications automatically via filesystem watcher
- Single-instance enforcement with IPC messaging
- Works on X11 and Wayland

## Requirements

- Python 3.11 or newer
- PyQt6 >= 6.4
- watchdog >= 3.0

## Installation

### Binary tarball (recommended for most users)

Download the latest `linxpad-VERSION-linux.tar.gz` from the [Releases](https://github.com/apapamarkou/linxpad/releases) page, extract it, and run the installer:

```bash
tar -xzf linxpad-1.0.0-linux.tar.gz
cd linxpad-1.0.0-linux
./install
```

The installer detects your distribution, installs any missing dependencies, and sets up the application and desktop entry automatically. Pass `--non-interactive` to skip all prompts.

### Distribution packages

| Format | Distros |
|--------|---------|
| RPM | Fedora 42, 43 · openSUSE Tumbleweed |
| DEB | Debian 12, 13 · Ubuntu 22.04, 24.04, 25.04 |
| Arch | `PKGBUILD` via AUR or manual |
| AppImage | Any Linux (x86\_64) |
| Flatpak | Any Linux with Flatpak installed |

Download the appropriate package from the [Releases](https://github.com/apapamarkou/linxpad/releases) page and install with your package manager.

### From source (git clone)

```bash
git clone https://github.com/apapamarkou/linxpad.git
cd linxpad
./install
```

Or install in editable mode for development:

```bash
make install
```

## Usage

Launch from your application menu, or run from the terminal:

```bash
linxpad
```

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Esc` | Close launcher |
| `←` / `→` | Navigate icons |
| `PgUp` / `PgDn` | Navigate pages |
| Type anything | Open search |

### Configuration

Settings are stored in `~/.config/linxpad/`:

| File | Purpose |
|------|---------|
| `settings.conf` | Grid layout, font size, transparency, launch mode |
| `apps.json` | Application order, folder assignments |

Example `settings.conf`:

```ini
# Grid layout
rows=3
cols=8

# Icon label font size (points, 8–32)
font-size=14

# Background transparency (0 = fully transparent, 100 = opaque)
transparency=75

# Launch mode: full-screen or window
launch-as=full-screen

# Restore previous search/folder state on reopen: yes or no
keep-previous-state=yes
```

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for significant changes.

See [docs/developer-usage.md](docs/developer-usage.md) for how to set up a development environment.

## License

LinxPad is released under the [GNU General Public License v3.0 or later](LICENSE).
