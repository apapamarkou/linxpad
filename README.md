# LinxPad

A macOS-style fullscreen application launcher for Linux, supporting both X11 and Wayland sessions.

[![Release](https://img.shields.io/github/v/release/apapamarkou/pipewire-controller?style=for-the-badge)](https://github.com/apapamarkou/pipewire-controller/releases)
[![License](https://img.shields.io/github/license/apapamarkou/pipewire-controller?style=for-the-badge)](LICENSE)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/andrianos)
---

<https://youtu.be/_Jiiq7-NmmA>

| Video | Screenshots |
|--------|---------|
|[![Watch the video](https://img.youtube.com/vi/_Jiiq7-NmmA/0.jpg)](https://www.youtube.com/watch?v=_Jiiq7-NmmA)|<img width="1920" height="1080" alt="Screenshot-Settings" src="https://github.com/user-attachments/assets/5d558029-1bc3-4560-85ca-f0a88052df84" />|
|<img width="1920" height="1080" alt="Screenshot-OrganizeInPagesAndFolders" src="https://github.com/user-attachments/assets/6c2af5e9-5008-415b-866a-dc627df9c6fb" />|<img width="1920" height="1080" alt="Screenshot-AppFolder" src="https://github.com/user-attachments/assets/71cf7864-c0d1-4242-8b36-6a64ef3d7e48" />|
|<img width="1920" height="1080" alt="Screenshot-Search-Apps-and-Folders" src="https://github.com/user-attachments/assets/51892dbd-2b9e-4140-84df-240b1ba43160" />|<img width="1920" height="1080" alt="Screenshot-Search-Web" src="https://github.com/user-attachments/assets/88f7f5e9-a08c-4195-9aad-0f7ffd599a4f" />|

## Features

- Full-screen grid of application icons
- Drag-and-drop folder grouping
- Drag-and-drop reordering
- Multi-page navigation with page indicator dots
- Integrated search — apps, files, and web
- Settings panel
- Live reload — detects new/removed applications automatically
- Works on X11 and Wayland
- Works on any desktop environment or window manager (even the tilling ones)
- Keyboard navigation and launch

## Requirements

- Python 3.11 or newer
- PyQt6 >= 6.4
- watchdog >= 3.0

The requirements are automatically handled by the installers.

## Installation

### Binary tarball (recommended for most users)

Download the latest `linxpad-VERSION-linux.tar.gz` from the [Releases](https://github.com/apapamarkou/linxpad/releases) page, extract it, and run the installer:

```bash
tar -xzf linxpad-1.0.0-linux.tar.gz
cd linxpad-1.0.0-linux
./install
```

The installer detects your distribution, installs any missing dependencies, and sets up the application and desktop entry automatically. Pass `--non-interactive` to skip all prompts.

### Packages

| Format | Distros |
|--------|---------|
| RPM | Fedora 42, 43 · openSUSE Tumbleweed |
| DEB | Debian 12, 13 · Ubuntu 22.04, 24.04, 25.04 |
| Arch | `PKGBUILD` manual |
| AppImage | Any Linux Distro (x86\_64) |

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
| Arrows | Navigate in pages, folders and search results |
| `PgUp` / `PgDn` | Navigate pages |
| Type anything | Open search |

### Configuration

Settings are stored in `~/.config/linxpad/`:

| File | Purpose |
|------|---------|
| `settings.conf` | Settings panel data |
| `apps.json` | Application order, folder assignments |

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for significant changes.

See [docs/developer-usage.md](docs/developer-usage.md) for how to set up a development environment.

## License

LinxPad is released under the [GNU General Public License v3.0 or later](LICENSE).
