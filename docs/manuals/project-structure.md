# Project Structure

```
linxpad/
├── install                          # Installer script (git clone + tarball users)
├── Makefile                         # Developer workflow targets
├── pyproject.toml                   # Project metadata, dependencies, tool config
├── LICENSE
├── README.md
│
├── src/linxpad/                     # Application source package
│   ├── main.py                      # Entry point — wires all services and launches UI
│   ├── __init__.py
│   │
│   ├── core/                        # Application state and background workers
│   │   ├── launcher_state.py        # Central state: app list, folders, page layout
│   │   └── scanner_worker.py        # Background thread for desktop file scanning
│   │
│   ├── models/                      # Plain data classes
│   │   ├── application.py           # Application entry (name, icon, exec, position)
│   │   └── folder.py                # Folder (name, icon, contained app IDs)
│   │
│   ├── services/                    # I/O and system integration
│   │   ├── config.py                # Reads/writes ~/.config/linxpad/apps.json
│   │   ├── settings.py              # Reads/writes ~/.config/linxpad/settings.conf
│   │   ├── desktop.py               # Scans /usr/share/applications for .desktop files
│   │   ├── desktop_watcher.py       # watchdog-based filesystem watcher for live reload
│   │   ├── icons.py                 # Resolves icon names to QIcon instances
│   │   ├── filesearch.py            # File search backend
│   │   ├── websearch.py             # Web search URL builder
│   │   └── settings.py              # UI settings (grid dimensions, font, transparency)
│   │
│   ├── ui/                          # All Qt UI code
│   │   ├── window.py                # Main launcher window (QMainWindow)
│   │   ├── theme.py                 # Colour palette and stylesheet constants
│   │   ├── settings_view.py         # Settings panel widget
│   │   │
│   │   ├── graphics/                # QGraphicsScene/QGraphicsView layer
│   │   │   ├── grid_view.py         # QGraphicsView — the main icon grid
│   │   │   ├── page_scene.py        # QGraphicsScene — one page of icons
│   │   │   ├── icon_item.py         # QGraphicsItem — single application icon
│   │   │   ├── drag_handler.py      # Drag-and-drop reordering logic
│   │   │   └── dots_indicator.py    # Page navigation dots widget
│   │   │
│   │   ├── views/                   # Overlay views (search, folder)
│   │   │   ├── search_view.py       # Full-screen search overlay
│   │   │   └── folder_view.py       # Folder contents overlay
│   │   │
│   │   ├── components/              # Reusable UI sub-widgets
│   │   │   ├── search_row.py        # A single result row in search view
│   │   │   ├── web_row.py           # Web search result row
│   │   │   ├── base_row.py          # Base class for result rows
│   │   │   ├── section_header.py    # Section label in search results
│   │   │   ├── inline_title.py      # Editable inline title widget
│   │   │   └── icon_utils.py        # Icon rendering helpers
│   │   │
│   │   └── services/
│   │       └── search_service.py    # Aggregates app, file, and web search results
│   │
│   ├── utils/
│   │   └── single_instance.py       # Unix socket-based single-instance + IPC
│   │
│   └── icons/                       # Bundled application icons
│       ├── linxpad.png
│       └── linxpad-folder.png
│
├── tests/                           # Pytest test suite (headless)
│   ├── test_config.py
│   ├── test_desktop.py
│   ├── test_desktop_watcher.py
│   ├── test_drag_handler.py
│   ├── test_grid_view.py
│   ├── test_icon_item.py
│   ├── test_launcher_state.py
│   ├── test_page_scene.py
│   └── test_rescan.py
│
├── docs/                            # Developer documentation
│   ├── developer-usage.md           # Dev environment setup and workflow
│   ├── packaging-and-testing.md     # How to build and test packages
│   ├── release-howto.md             # Step-by-step release process
│   └── project-structure.md         # This file
│
└── packaging/
    ├── distro-versions.conf         # Single source of truth for target versions
    │
    ├── specs/
    │   ├── linxpad.spec             # RPM spec (used by Fedora + openSUSE builds)
    │   └── linxpad.desktop          # XDG desktop entry file
    │
    ├── debian/
    │   ├── control                  # Debian package metadata and dependencies
    │   ├── rules                    # Debhelper build rules
    │   └── changelog                # Debian changelog
    │
    ├── flatpak/
    │   └── io.github.apapamarkou.linxpad.yaml   # Flatpak manifest
    │
    ├── scripts/                     # Build and orchestration scripts
    │   ├── build-fedora-rpm.sh      # Builds RPM for a given Fedora version
    │   ├── build-opensuse-rpm.sh    # Builds RPM for openSUSE Tumbleweed/Leap
    │   ├── build-deb.sh             # Builds .deb for Debian or Ubuntu
    │   ├── build-arch-pkgbuild.sh   # Generates PKGBUILD and builds Arch package
    │   ├── build-appimage.sh        # Builds fat AppImage (bundles Python + Qt)
    │   ├── build-flatpak.sh         # Builds Flatpak bundle
    │   ├── build-tarball.sh         # Builds binary tarball with installer
    │   ├── build-src-tarball.sh     # Builds source tarball via git archive
    │   ├── packages.sh              # Interactive package builder menu
    │   ├── release.sh               # Non-interactive CI release script
    │   └── test-packages.sh         # Package installation test orchestrator
    │
    ├── tests/                       # Per-format Docker-based install tests
    │   ├── test-fedora-rpm.sh
    │   ├── test-opensuse-rpm.sh
    │   ├── test-deb.sh
    │   ├── test-arch-pkg.sh
    │   ├── test-flatpak.sh
    │   └── test-tarball.sh
    │
    └── output/                      # Built packages land here (git-ignored)
        └── arch/                    # Arch packages in a subdirectory
```

## Key design decisions

**`src/` layout** — the package lives under `src/linxpad/` rather than at the root, preventing accidental imports of the source tree when running tests against an installed version.

**QGraphicsScene/QGraphicsView** — the icon grid uses Qt's graphics scene architecture rather than a widget grid. This gives precise control over layout, animation, and drag-and-drop at the cost of more manual geometry management.

**Pre-built wheel pattern** — all Docker build scripts build the wheel on the host first, then mount it into the container. This means containers only need `pip` and the target distro's runtime dependencies — no build tools, no `hatchling`, no internet access inside the container.

**`distro-versions.conf` as single source of truth** — adding a new distro version to the conf file is the only change needed to include it in all build and test runs.

**`import linxpad.core` in tests** — top-level `import linxpad` triggers Qt initialisation, which fails in headless containers. All package install tests import `linxpad.core` instead, which is pure Python.
