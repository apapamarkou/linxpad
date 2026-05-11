# Developer Usage

## Prerequisites

- Python 3.11 or newer
- `pip`, `ruff`, `black`, `pytest`
- A running X11 or Wayland session (required to launch the UI)

Install Python dev dependencies:

```bash
pip install -e ".[dev]"
# or manually:
pip install PyQt6 watchdog ruff black pytest
```

## Option A — VSCode Dev Container (recommended)

Provides a fully reproducible environment without touching your host Python.

### Host prerequisites (Fedora / openSUSE)

1. Install Podman and the socket unit:
   ```bash
   # Fedora
   sudo dnf install podman
   # openSUSE
   sudo zypper install podman

   # Enable the rootless socket (required by the Dev Containers extension)
   systemctl --user enable --now podman.socket
   ```

2. Tell VSCode to use Podman instead of Docker — add to your **host** VSCode
   `settings.json`:
   ```json
   {
       "dev.containers.dockerPath": "podman",
       "docker.environment": {
           "DOCKER_HOST": "unix:///run/user/${env:UID}/podman/podman.sock"
       }
   }
   ```
   Or set the environment variable in your shell profile:
   ```bash
   export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
   ```

3. Install the **Dev Containers** extension (`ms-vscode-remote.remote-containers`).

### Opening the project in the container

1. Open the `linxpad` folder in VSCode.
2. Press `Ctrl+Shift+P` → **Dev Containers: Reopen in Container**.
3. VSCode builds the image (first time ~2 min), then reopens inside it.
4. The project is installed in editable mode automatically (`postCreateCommand`).

All `make` targets, `pytest`, `ruff`, and `black` work immediately in the
integrated terminal.

### Rebuilding the container

If you change `Dockerfile` or `requirements-dev.txt`:
```
Ctrl+Shift+P → Dev Containers: Rebuild Container
```

---

## Option B — Local setup

## Setting up the development environment

```bash
git clone https://github.com/apapamarkou/linxpad.git
cd linxpad
make install
```

`make install` installs the package in editable mode (`pip install -e .`) and registers the desktop entry and icons under `~/.local/share/`.

## Running LinxPad

```bash
linxpad
```

Or directly from the source tree without installing:

```bash
PYTHONPATH=src python3 -m linxpad.main
```

## Makefile targets

| Target | Description |
|--------|-------------|
| `make install` | Install in editable mode + desktop entry |
| `make uninstall` | Remove installed files |
| `make wipe` | Remove installed files and config (`~/.config/linxpad`) |
| `make test` | Run the test suite with pytest |
| `make lint` | Check code style with ruff and black |
| `make format` | Auto-fix style issues |
| `make check` | Run lint then tests |
| `make packages` | Build all packages non-interactively |
| `make package` | Interactive package builder |
| `make test-packages` | Run all package installation tests non-interactively |
| `make test-package` | Run selected package tests interactively |
| `make release` | Full non-interactive CI release build |

## Running tests

```bash
make test
# or
python3 -m pytest tests/ -v
```

Tests are located in `tests/` and cover core state management, desktop scanning, drag handling, grid view, icon items, page scenes, and the filesystem watcher. They are headless — no display required.

## Code style

The project uses `ruff` for linting and `black` for formatting, both configured in `pyproject.toml`.

```bash
make lint      # check only
make format    # auto-fix
```

Line length is 100 characters. Target Python version is 3.11.

## Configuration during development

LinxPad reads its configuration from `~/.config/linxpad/`. On first run it creates `settings.conf` with defaults. You can edit this file directly while developing — changes take effect on the next launch.

To reset to defaults, delete the config directory:

```bash
rm -rf ~/.config/linxpad
```

## Uninstalling

```bash
make uninstall
```

This removes the pip-installed package, the desktop entry, and the application icons.

To also delete configuration files (`~/.config/linxpad`):

```bash
make wipe
# or
./uninstall --wipe
```
