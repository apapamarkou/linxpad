## What's new in v1.4.0

### Bug fixes

- **Icon disappearance: stale cached path** — icons no longer go blank when a cached icon path is deleted from disk (e.g. after a package reinstall). The fallback chain now shows the app's letter-avatar instead of an empty slot.
- **Icon disappearance: SVG without Qt plugin** — apps with SVG icons no longer show blank slots on systems where the Qt SVG plugin is unavailable. The letter-avatar fallback is used instead.
- **Icon disappearance: transient .desktop absence** — apps no longer vanish from the grid during a brief scan miss (e.g. a slow filesystem or mid-update state). An app must be absent for 3 consecutive scans before it is removed.
- **Drag overflow to full page** — dragging an app onto a page that is exactly full no longer overflows sort positions into the next page's slot range. The move is now correctly blocked.
- **Icon size parser (retina directories)** — icon resolution no longer picks the wrong size on systems with retina-style icon directories (e.g. `2x-retina`). The parser now requires a strict `NxN` format (both sides equal integers).
- **Stale icon cache** — `IconResolver` now evicts cache entries whose paths no longer exist on disk and re-resolves, so a replacement theme icon is found after reinstalling a package.

### Other changes

- Install script gained `--global` and non-interactive mode flags for scripted deployments.

---

**Full changelog:** https://github.com/apapamarkou/linxpad/compare/v1.3.0...v1.4.0
