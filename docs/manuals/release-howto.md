# Creating a New Release

## Checklist

Before starting a release, make sure:

- All intended changes are committed and pushed
- The test suite passes: `make check`
- You have Docker installed and running (required for package builds)
- You are on the `main` branch with a clean working tree

## Step 1 — Bump the version

The version is defined in one place:

```
pyproject.toml
```

```toml
[project]
version = "1.1.0"
```

Update it, then commit:

```bash
git add pyproject.toml
git commit -m "chore: bump version to 1.1.0"
```

## Step 2 — Tag the release

```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main --tags
```

## Step 3 — Build all packages

### Option A — Automated (CI / non-interactive)

```bash
make release
```

This runs `packaging/scripts/release.sh`, which:

1. Runs `ruff`, `black`, and `pytest` as pre-flight checks
2. Verifies the working tree is clean
3. Builds every package type for every version in `distro-versions.conf`
4. Runs the full package installation test suite
5. Prints a summary of all outputs

The script exits non-zero on any failure, making it safe to use in CI pipelines.

### Option B — Interactive (local, selective)

```bash
make packages
```

Use the interactive menu to build only the package types and versions you need.

## Step 4 — Test packages

If you used `make release`, testing ran automatically. To run tests separately:

```bash
make test-packages
```

Or interactively to select specific distros:

```bash
make test-packages-interactive
```

All built packages must pass before publishing. See [packaging-and-testing.md](packaging-and-testing.md) for details on what each test verifies.

## Step 5 — Publish the release on GitHub

1. Go to [github.com/apapamarkou/linxpad/releases](https://github.com/apapamarkou/linxpad/releases)
2. Click **Draft a new release**
3. Select the tag you created in Step 2
4. Set the release title to `v1.1.0`
5. Write release notes (features, fixes, breaking changes)
6. Upload all files from `packaging/output/`:
   - `linxpad-1.1.0-linux.tar.gz` (binary tarball)
   - `linxpad-1.1.0.tar.gz` (source tarball)
   - `linxpad-1.1.0-1.fc43.noarch.rpm`
   - `linxpad-1.1.0-1.opensusetumbleweed.noarch.rpm`
   - `linxpad_1.1.0-1_all~24.04.deb`
   - `linxpad_1.1.0-1_all~13.deb`
   - `packaging/output/arch/linxpad-1.1.0-1-any.pkg.tar.zst`
   - `LinxPad-1.1.0-x86_64.AppImage`
7. Click **Publish release**

## Adding new target distro versions

To add a new distro version to future releases, edit `packaging/distro-versions.conf`:

```ini
fedora-versions=44,43,42
ubuntu-versions=25.04,24.04,22.04
```

Each comma-separated value will produce a separate package build and test run. No other files need to change.

## Troubleshooting

**Pre-flight lint fails** — run `make format` to auto-fix style issues, then re-commit.

**A package build fails with exit code 2** — Docker is not available or the image could not be pulled. Check your Docker daemon and network connectivity.

**A package test fails** — run the individual test script directly (see [packaging-and-testing.md](packaging-and-testing.md)) to see the full container output. Common causes are missing dependencies in the base image or a changed package name in the distro's repositories.

**Working tree is not clean** — `release.sh` refuses to proceed if there are uncommitted changes. Commit or stash everything before running `make release`.
