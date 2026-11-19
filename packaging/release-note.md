## What's new in v1.5.0

### New feature — Icon theme awareness

LinxPad now detects the user's desktop icon theme at startup and resolves application icons from that theme instead of always defaulting to Breeze.

- **Automatic theme detection** — the active icon theme is read from KDE (`kdeglobals`), XFCE (`xsettings.xml`), LXDE/LXQt (`desktop.conf`), and GNOME/Cinnamon (`gsettings`). When no theme can be detected, the previous Breeze-first behaviour is kept as a fallback.
- **Qt theme integration** — `QIcon.setThemeName()` is called at startup so `QIcon.fromTheme()` lookups also honour the user's theme on KDE, XFCE, and LXDE.
- **Higher-priority resolution** — `IconResolver` now accepts a `detected_theme` argument. When supplied, icons in that theme score above Breeze-Dark and Breeze, so the user-configured theme always wins.
- **Rescan path updated** — theme detection runs on every rescan as well, keeping icons consistent after a theme change without restarting.

---

**Full changelog:** https://github.com/apapamarkou/linxpad/compare/v1.4.0...v1.5.0
