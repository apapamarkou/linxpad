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
| `make test` | Run the test suite with pytest |
| `make lint` | Check code style with ruff and black |
| `make format` | Auto-fix style issues |
| `make check` | Run lint then tests |
| `make packages` | Interactive package builder |
| `make test-packages` | Run all package installation tests |
| `make test-packages-interactive` | Run selected package tests interactively |
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

This removes the pip-installed package, the desktop entry, and the application icon.
