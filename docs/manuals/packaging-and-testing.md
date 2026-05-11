# Packaging and Testing

## Overview

All packaging is Docker-based. Each build script spins up a clean container for the target distro, builds the package inside it, and writes the output to `packaging/output/`. Docker must be installed and running on the host.

The pre-built wheel pattern is used throughout: the wheel is built once on the host with `python3 -m pip wheel`, mounted into the container as `/wheels`, and installed with `pip install --no-deps`. This avoids requiring `hatchling` or a matching Python version inside the container.

## Target versions

Target distro versions are defined in a single file:

```
packaging/distro-versions.conf
```

```ini
fedora-versions=43
opensuse-versions=tumbleweed
debian-versions=13
ubuntu-versions=24.04
```

Each comma-separated value produces a separate package. Add or remove versions here to change what gets built and tested.

## Building packages

### Build all packages (non-interactive)

```bash
make packages
# or
bash packaging/scripts/packages.sh
```

### Interactive builder (select what to build)

```bash
make package
# or
bash packaging/scripts/packages.sh --interactive
```

Presents a two-layer menu: first select the package type, then (for multi-version distros) select which versions to build.

```
  1) Source tarball
  2) Binary tarball
  3) openSUSE RPM
  4) Fedora RPM
  5) Debian .deb
  6) Ubuntu .deb
  7) Arch PKGBUILD
  8) AppImage
  9) Flatpak
  a) All of the above
```

### Building individual package types

Each build script can also be run directly:

```bash
bash packaging/scripts/build-fedora-rpm.sh 43
bash packaging/scripts/build-opensuse-rpm.sh tumbleweed
bash packaging/scripts/build-deb.sh 24.04        # Ubuntu
bash packaging/scripts/build-deb.sh 13            # Debian (integer = Debian)
bash packaging/scripts/build-arch-pkgbuild.sh
bash packaging/scripts/build-appimage.sh
bash packaging/scripts/build-flatpak.sh
bash packaging/scripts/build-tarball.sh           # binary tarball
bash packaging/scripts/build-src-tarball.sh       # source tarball
```

All output lands in `packaging/output/`.

### Output file naming

| Package | Filename pattern |
|---------|-----------------|
| Fedora RPM | `linxpad-VERSION-1.fcVER.noarch.rpm` |
| openSUSE RPM | `linxpad-VERSION-1.opensuseVER.noarch.rpm` |
| Debian .deb | `linxpad_VERSION-1_all~VER.deb` |
| Ubuntu .deb | `linxpad_VERSION-1_all~VER.deb` |
| Arch package | `packaging/output/arch/linxpad-VERSION-1-any.pkg.tar.zst` |
| AppImage | `LinxPad-VERSION-x86_64.AppImage` |
| Flatpak bundle | `LinxPad-VERSION.flatpak` |
| Binary tarball | `linxpad-VERSION-linux.tar.gz` |
| Source tarball | `linxpad-VERSION.tar.gz` |

## Testing packages

Package tests install each built package into a clean Docker container for the target distro and verify:

1. The package installs without errors
2. `linxpad` binary or entry point is present
3. `python3 -c 'import linxpad.core'` succeeds (Qt-free import, works headlessly)
4. The `.desktop` file and icon are installed in the expected locations

### Run all tests (non-interactive)

```bash
make test-packages
# or
bash packaging/scripts/test-packages.sh
```

### Run tests interactively (select which to run)

```bash
make test-package
# or
bash packaging/scripts/test-packages.sh --interactive
```

### Run a single test script directly

```bash
bash packaging/tests/test-fedora-rpm.sh    packaging/output/linxpad-1.0.0-1.fc43.noarch.rpm 43
bash packaging/tests/test-opensuse-rpm.sh  packaging/output/linxpad-1.0.0-1.opensusetumbleweed.noarch.rpm tumbleweed
bash packaging/tests/test-deb.sh           packaging/output/linxpad_1.0.0-1_all~24.04.deb 24.04
bash packaging/tests/test-arch-pkg.sh      packaging/output/arch/linxpad-1.0.0-1-any.pkg.tar.zst
bash packaging/tests/test-flatpak.sh       packaging/output/LinxPad-1.0.0.flatpak
bash packaging/tests/test-tarball.sh       packaging/output/linxpad-1.0.0-linux.tar.gz fedora:43 "Fedora 43"
```

### Test exit codes

| Code | Meaning |
|------|---------|
| `0` | Pass |
| `1` | Fail |
| `2` | Skipped (Docker not available) |

## Notes on specific package types

### openSUSE RPM

The spec is patched at build time to replace `python3-pyqt6` (Fedora name) with `python3-qt6` (openSUSE name). The test uses `--no-gpg-checks` because the RPM is unsigned.

### Debian / Ubuntu .deb

The build script detects Debian vs Ubuntu by version string format (integer = Debian, `x.xx` = Ubuntu). It uses `--break-system-packages` and a `dpkg --force-depends` fallback for distros where PyQt6 is not in the base repo.

### AppImage

The AppImage bundles Python 3.11, PyQt6, Qt6 libraries, and watchdog. It is built inside `ubuntu:24.04` using `python-appimage`. No headless test is possible for AppImage — it is excluded from `test-packages`.

### Flatpak

Built inside Docker with `--disable-rofiles-fuse`. Wheels are pre-downloaded at the Docker level to work around Flatpak's network-isolated module builds. The icon is installed as `io.github.apapamarkou.linxpad.png` and the `Icon=` key in the desktop file is patched with `desktop-file-edit`.

### Binary tarball

Contains the pre-built wheel, assets, and the `install` script. The installer auto-detects the distro and installs missing dependencies. See the tarball test for how this is verified across all supported distros.
