# Icon Disappearance Fix Bugfix Design

## Overview

LinxPad icons disappear intermittently along a pipeline that flows from desktop
scanning, through icon resolution and caching, into pixmap loading and rendering.
Five distinct defects cause icons to vanish or the grid to corrupt instead of
degrading gracefully:

1. **Stale cached icon path** (Bug 1.1): The icon loader returns a null pixmap when
   a cached resolved path no longer exists on disk (theme uninstalled or package
   updated), instead of falling back to a letter-avatar.
2. **SVG without Qt plugin** (Bug 1.2): SVG/SVGZ icons become null pixmaps when the
   Qt SVG image format plugin is unavailable, with no fallback check.
3. **Transient .desktop absence** (Bug 1.3): A filesystem rescan during a package
   update deletes apps whose .desktop files are transiently unavailable, discarding
   their UUIDs and grid positions.
4. **Full-page drag overflow** (Bug 1.4): Dragging an item onto an already-full page
   overflows the layout into the next page because the capacity check uses a
   strictly-greater-than test that misses the exactly-full case.
5. **Icon size misparse** (Bug 1.5): The size parser misparses path components like
   "2x-retina" and selects the wrong-sized icon.

The fix strategy is surgical — each defect is addressed at its precise location with
minimal changes, preserving all existing behavior for non-buggy inputs:

- **Bugs 1.1 & 1.2** share a single fix location (`icon_utils.py`): add `os.path.exists()`
  and `QPixmap.isNull()` guards at every `make_pixmap()` call site in the fallback
  chain, falling through to `_fallback()` when any path yields a null pixmap.
- **Bug 1.3** adds a grace-period counter in `LauncherState.apply_scan_results()` —
  apps are retained for N consecutive absent scans (default 3) before removal, with
  the count reset on reappearance.
- **Bug 1.4** is a one-character fix: change `>` to `>=` in the capacity check.
- **Bug 1.5** tightens the `_parse_size()` matcher to only accept true "NxN"
  components (both sides digits, equal values) and skip non-matching "x" components.

## Glossary

- **Bug_Condition (C)**: The union of five conditions that trigger the bugs — C₁
  (stale/null icon path), C₂ (SVG without plugin), C₃ (transient .desktop absence),
  C₄ (full-page drag), C₅ (non-NxN "x" path component). Formally: C = C₁ ∨ C₂ ∨ C₃ ∨ C₄ ∨ C₅.
- **Property (P)**: The desired behavior for each bug condition — non-null pixmap
  fallback (P₁), grace-period retention (P₂), blocked full-page drag (P₃), correct
  NxN size parsing (P₄).
- **Preservation**: All existing behavior for inputs that do NOT satisfy any bug
  condition — valid icon rendering, permanent uninstall removal, non-full-page drag
  insertion, "scalable" size precedence, and new-app sort appending.
- **IconResolver**: The class in `src/linxpad/services/icons.py` that resolves icon
  names to file paths via filesystem search, with an in-memory cache (`_cache` dict).
- **make_pixmap**: The function in `src/linxpad/ui/components/icon_utils.py` that
  loads a `QPixmap` from a file path and scales it. Returns a null `QPixmap` when
  the file is missing, corrupt, or uses an unsupported format (e.g. SVG without plugin).
- **app_pixmap**: The function in `icon_utils.py` that returns a `QPixmap` for an app
  item using a fallback chain: stored icon path → Qt theme icon → IconResolver →
  letter-avatar. This is the primary fix location for Bugs 1.1 and 1.2.
- **load_app_icon**: The function in `icon_utils.py` that loads an app icon into a
  `QLabel`. Duplicates `app_pixmap`'s fallback chain. Used by `SearchRow` for search
  result icons. Will be refactored to delegate to `app_pixmap`.
- **_fallback**: The function in `icon_utils.py` that draws a letter-avatar pixmap —
  a non-null `QPixmap` showing the uppercased first character of the app name (or "?"
  when empty).
- **LauncherState**: The class in `src/linxpad/core/launcher_state.py` that holds all
  mutable launcher data and business logic. Contains `apply_scan_results()`,
  `_reorder_main()`, and the page-size constant `PAGE_SIZE` (default 24).
- **absence_count**: A per-app counter tracking consecutive scans in which the app's
  .desktop file was absent from scan results. Stored in `LauncherState._absence_counts`
  (transient, not persisted). When count ≥ N (grace period), the app is removed.
- **_parse_size**: The static method on `IconResolver` that extracts an integer size
  from an icon path by inspecting path components. Used to sort icon candidates by
  size (largest wins).
- **page_size**: The maximum number of items per grid page (`LauncherState._page_size`,
  default 24 = 8 columns × 3 rows). Determines the sort-id slot range per page.
- **NxN size directory**: A path component consisting of a digit sequence, the
  character "x", and a second digit sequence of equal value (e.g. "48x48", "16x16").
  The size is the integer value of either digit sequence.

## Bug Details

### Bug Condition

The five bugs manifest under five distinct conditions. Each is formalized below.

**C₁ — Stale cached icon path (Bug 1.1)**

The bug manifests when the icon resolver returns a cached path for an app's icon
name, the file at that cached path no longer exists on disk, and the icon loader
returns the resulting null pixmap instead of falling through to the letter-avatar.

```
FUNCTION isBugCondition_stale_path(item, icon_resolver)
  INPUT: item of type dict (app item), icon_resolver of type IconResolver
  OUTPUT: boolean

  icon_path := item.get("icon")
  icon_name := item.get("icon_name")

  // Case A: stored icon_path exists but yields a null pixmap
  // (e.g. SVG without plugin — covered by C₂, but also caught here)
  IF icon_path IS NOT None AND os.path.exists(icon_path)
     AND make_pixmap(icon_path, size).isNull() THEN
    RETURN True

  // Case B: icon resolver returns a cached path whose file no longer exists
  IF icon_name IS NOT None AND icon_resolver IS NOT None THEN
    resolved := icon_resolver.resolve(icon_name)
    IF resolved IS NOT None AND NOT os.path.exists(resolved) THEN
      RETURN True
  END IF

  RETURN False
END FUNCTION
```

**C₂ — SVG icon without Qt SVG plugin (Bug 1.2)**

The bug manifests when the icon loader loads a pixmap from a resolved icon path
ending with `.svg` or `.svgz` (case-insensitive) whose file exists on disk, but
`QPixmap(path).isNull()` returns True because the Qt SVG image format plugin is
unavailable. The loader returns the null pixmap without checking `.isNull()`.

```
FUNCTION isBugCondition_svg_null(item, icon_resolver)
  INPUT: item of type dict (app item), icon_resolver of type IconResolver
  OUTPUT: boolean

  icon_path := item.get("icon")
  IF icon_path IS NOT None AND os.path.exists(icon_path) THEN
    ext := lower(os.path.splitext(icon_path)[1])
    IF ext IN ['.svg', '.svgz'] AND QPixmap(icon_path).isNull() THEN
      RETURN True
  END IF

  IF icon_name IS NOT None AND icon_resolver IS NOT None THEN
    resolved := icon_resolver.resolve(icon_name)
    IF resolved IS NOT None AND os.path.exists(resolved) THEN
      ext := lower(os.path.splitext(resolved)[1])
      IF ext IN ['.svg', '.svgz'] AND QPixmap(resolved).isNull() THEN
        RETURN True
      END IF
    END IF
  END IF

  RETURN False
END FUNCTION
```

**C₃ — Transient .desktop file absence (Bug 1.3)**

The bug manifests when a .desktop file is transiently unavailable during a package
update and a filesystem rescan is triggered. The app is immediately removed from
state — its UUID discarded, its grid page compacted, its icon disappears — instead
of being retained for a grace period.

```
FUNCTION isBugCondition_transient_absence(state, found)
  INPUT: state of type LauncherState, found of type list[dict] (scan results)
  OUTPUT: boolean

  found_keys := {(a["name"], a["exec"]) for a in found}
  FOR EACH (key, app_id) IN managed_keys(state) DO
    IF key NOT IN found_keys THEN
      // App absent this scan — bug triggers if removed immediately
      // (without grace period). Fix: retain until absence_count >= N.
      IF app_id IN state.apps AND absence_count(app_id) < N THEN
        RETURN True  // bug: immediate removal instead of grace period
      END IF
    END IF
  END FOR
  RETURN False
END FUNCTION
```

**C₄ — Full-page drag overflow (Bug 1.4)**

The bug manifests when an item is dragged from a source page onto a target page on
which the dragged item is not already present and the number of items on the target
page equals page_size. The capacity check uses `len(page_ids) > page_size` which is
False when `len(page_ids) == page_size`, so the move proceeds and a sort position
overflows past the target page's slot range.

```
FUNCTION isBugCondition_full_page_drag(state, dragged_id, target_id)
  INPUT: state of type LauncherState, dragged_id, target_id of type str
  OUTPUT: boolean

  target_obj := state.apps.get(target_id) OR state.folders.get(target_id)
  IF target_obj IS None THEN RETURN False
  target_page := target_obj.sort_id // state._page_size

  page_ids := [id for id in main_item_ids(state)
               if sort_id(id) // state._page_size == target_page]

  dragged_obj := state.apps.get(dragged_id) OR state.folders.get(dragged_id)
  IF dragged_obj IS None THEN RETURN False

  IF dragged_id NOT IN page_ids THEN
    // Cross-page drag: bug when target page is exactly full
    IF len(page_ids) == state._page_size THEN
      RETURN True  // bug: > check misses == case, move overflows
    END IF
  END IF
  RETURN False
END FUNCTION
```

**C₅ — Non-NxN "x" path component (Bug 1.5)**

The bug manifests when an icon path contains, before any "NxN" size directory, a
path component that begins with a digit sequence followed by "x" and whose remainder
after "x" is not purely digits (for example "2x-retina"). The size parser returns
the integer value of that leading digit sequence instead of the size of the "NxN"
size directory.

```
FUNCTION isBugCondition_size_misparse(path)
  INPUT: path of type str (icon file path)
  OUTPUT: boolean

  parts := path.split(os.sep)
  IF "scalable" IN parts THEN RETURN False  // scalable takes precedence, no bug

  FOR EACH p IN parts DO
    IF "x" IN p THEN
      halves := p.split("x")
      IF len(halves) == 2 AND halves[0].isdigit() AND NOT halves[1].isdigit() THEN
        // Component like "2x-retina": first part is digits, second is not.
        // Bug: parser returns int(halves[0]) = 2 instead of continuing.
        RETURN True
      END IF
    END IF
  END FOR
  RETURN False
END FUNCTION
```

### Examples

**C₁ — Stale cached path:**
- App "Firefox" has `icon="/usr/share/icons/breeze-dark/48x48/firefox.png"` and
  `icon_name="firefox"`. The breeze-dark theme is uninstalled. On next render,
  `os.path.exists(icon_path)` is False, so the loader tries `icon_resolver.resolve("firefox")`
  which returns the cached stale path. `make_pixmap(stale_path)` returns null.
  **Expected**: letter-avatar "F". **Actual (unfixed)**: null pixmap, icon disappears.

**C₂ — SVG without plugin:**
- App "GIMP" has `icon="/usr/share/icons/hicolor/scalable/apps/gimp.svg"`. The file
  exists but the Qt SVG plugin is not installed. `QPixmap(svg_path).isNull()` is True.
  **Expected**: letter-avatar "G". **Actual (unfixed)**: null pixmap, icon disappears.

**C₃ — Transient absence:**
- App "Firefox" (UUID "abc-123", sort_id=5) is in state. During a package update,
  its .desktop file is temporarily removed. A watcher-triggered rescan finds it absent.
  **Expected**: app retained (count=1, < N=3), UUID and sort_id unchanged.
  **Actual (unfixed)**: app deleted, page compacted, icon disappears. On reappearance,
  re-added with new UUID at max_sort+1 (different grid position).

**C₄ — Full-page drag:**
- Page 0 has exactly `page_size` (24) items. App "x50" on page 2 is dragged onto
  page 0 targeting app "x05". `len(page_ids) == 24`, `24 > 24` is False, move proceeds.
  **Expected**: move blocked, no sort positions modified. **Actual (unfixed)**: item
  inserted, slot 24 (= page 1 slot 0) assigned, grid layout corrupted.

**C₅ — Size misparse:**
- Icon path `/usr/share/icons/Adwaita/2x-retina/apps/firefox.png` — the parser hits
  "2x-retina" first, `p.split("x")[0]` = "2", `"2".isdigit()` is True, returns 2.
  **Expected**: "2x-retina" ignored (not NxN), continue scanning, return 0 (no NxN
  directory present). **Actual (unfixed)**: returns 2, wrong icon size selected.

- Icon path `/usr/share/icons/breeze/16x16/apps/firefox.png` — parser correctly
  returns 16. This is NOT a bug condition (both sides are digits and equal).

- Icon path `/usr/share/icons/Adwaita/2x-retina/48x48/apps/firefox.png` — parser
  hits "2x-retina" first and returns 2. **Expected**: skip "2x-retina", find "48x48",
  return 48. **Actual (unfixed)**: returns 2.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- When an icon's resolved path is valid (file exists and yields a non-null pixmap),
  the system SHALL continue to render the icon from that path. (Req 3.1)
- When the icon loader loads a pixmap from a `.svg`/`.svgz` path and the Qt SVG
  plugin IS available (`isNull()` returns False), the system SHALL continue to return
  the non-null SVG-rendered pixmap. (Req 3.2)
- When a .desktop file has been absent for N or more consecutive scans (permanent
  uninstall), the system SHALL continue to remove the app and compact the grid. (Req 3.3)
- When dragging onto a target page with fewer than page_size items (and the dragged
  item is not already present), the system SHALL continue to insert the item and
  reassign sort positions within the page's slot range. (Req 3.4)
- When an icon path contains "scalable" as a path component, the size parser SHALL
  continue to return 9999, taking precedence over any "NxN" directory. (Req 3.5)
- When an app has neither a valid icon path nor a resolvable icon name, the system
  SHALL continue to render the letter-avatar fallback. (Req 3.6)
- When apps are first discovered via scan, the system SHALL continue to add them with
  new identifiers appended after the current maximum sort position. (Req 3.7)

**Scope:**
All inputs that do NOT satisfy any bug condition (C₁–C₅) should be completely
unaffected by these fixes. This includes:
- Valid icon paths (file exists, non-null pixmap) — rendering unchanged
- SVG icons with plugin available — rendering unchanged
- Apps present in scan results — no absence counting, no removal
- Within-page reorders — sort reassignment unchanged
- Cross-page drags to non-full pages — insertion behavior unchanged
- Icon paths with "scalable" or valid "NxN" components — size parsing unchanged
- Pure-numeric path components (e.g. "48") — size parsing unchanged

## Hypothesized Root Cause

Based on code analysis, the root causes are:

1. **Missing null-pixmap guards in fallback chain (Bugs 1.1 & 1.2)**:
   - `app_pixmap()` calls `make_pixmap(icon_path, size)` and returns the result
     directly without checking `.isNull()`. When the file exists but `QPixmap(path)`
     is null (SVG without plugin, or corrupt file), the null pixmap is returned.
   - The resolver branch (`icon_resolver.resolve(icon_name)`) checks only `if resolved:`
     (truthy for any non-None string) without calling `os.path.exists()` on the
     resolved path. A cached stale path passes this check, and `make_pixmap` returns null.
   - `load_app_icon()` duplicates the same logic and has the same gaps.
   - The `QIcon.fromTheme(icon_name)` branch already checks `qi.isNull()`, so it is
     correct — the bug is only in the `make_pixmap` call sites.

2. **Immediate removal on absence without grace period (Bug 1.3)**:
   - `apply_scan_results()` iterates over managed apps and immediately `del`s any
     app whose (name, exec) key is not in `found_keys`. There is no absence counter
     or grace period — a single transient absence triggers removal.
   - When the .desktop file reappears, the app is re-added as a new entry with a
     fresh UUID and `sort_id = max_sort + 1`, losing its original grid position.

3. **Off-by-one in capacity comparison (Bug 1.4)**:
   - `_reorder_main()` uses `len(page_ids) > self._page_size` to block cross-page
     drags to full pages. When `len(page_ids) == page_size` (exactly full), this
     evaluates to False and the move proceeds. The reassignment loop then writes
     `page_size + 1` sort positions, with the last one (`base + page_size`)
     overflowing into the next page's first slot.

4. **Overly permissive "x" component matching (Bug 1.5)**:
   - `_parse_size()` checks `"x" in p` then takes `p.split("x")[0]` and tests
     `isdigit()`. For "2x-retina", `split("x")` gives `["2", "-retina"]`, and
     `"2".isdigit()` is True, so it returns 2. The parser never validates that the
     part after "x" is also digits (the "NxN" pattern), so non-size "x" components
     are mistaken for size directories.

## Correctness Properties

Property 1: Bug Condition - Non-Null Pixmap Fallback for Stale and SVG Paths

_For any_ app item where the bug condition holds (the stored icon path exists but
yields a null pixmap, or the icon resolver returns a cached path whose file does
not exist on disk, or a .svg/.svgz path yields a null QPixmap due to a missing Qt
SVG plugin), the fixed `app_pixmap` function SHALL return a non-null QPixmap —
specifically the letter-avatar fallback drawn from the uppercased first character
of the application name (or "?" when the name is empty) — so that the icon area
never renders blank.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Bug Condition - Grace Period Retention for Transient .desktop Absence

_For any_ app whose .desktop file is absent from scan results for fewer than N
consecutive scans (where N defaults to 3), the fixed `apply_scan_results` SHALL
retain the app in state with its identifier, grid position (sort_id), and folder
membership unchanged, incrementing only the internal absence counter. When the
.desktop file reappears before the count reaches N, the counter SHALL reset to
zero with all app attributes preserved.

**Validates: Requirements 2.5, 2.7**

Property 3: Bug Condition - Removal After Grace Period Exhaustion

_For any_ app whose .desktop file has been absent from scan results for N or more
consecutive scans (where N defaults to 3), the fixed `apply_scan_results` SHALL
remove the app from state and compact the grid page, exactly as the original code
did for a single absence — but only after the grace period is exhausted.

**Validates: Requirements 2.6**

Property 4: Bug Condition - Block Drag to Full Page

_For any_ drag operation where the dragged item is not already on the target page
and the number of items on the target page is greater than or equal to page_size,
the fixed `_reorder_main` SHALL block the move so that the dragged item remains at
its original sort position, no item's sort position is modified, and the grid
layout is unchanged.

**Validates: Requirements 2.8**

Property 5: Bug Condition - Correct NxN Size Parsing

_For any_ icon path that contains an "NxN" size directory (a component consisting of
a digit sequence, "x", and a second digit sequence of equal value), the fixed
`_parse_size` SHALL return N as the size, ignoring any preceding non-NxN "x"
components (where the part after "x" is not purely digits, such as "2x-retina").

**Validates: Requirements 2.9, 2.10**

Property 6: Preservation - Valid Icon and SVG Rendering

_For any_ app item where the bug condition does NOT hold (the stored icon path
exists and yields a non-null pixmap, or a .svg/.svgz path loads successfully with
the Qt SVG plugin available, or the app has neither a valid path nor a resolvable
name), the fixed `app_pixmap` SHALL produce exactly the same non-null pixmap as
the original function, preserving all existing icon rendering and fallback behavior.

**Validates: Requirements 3.1, 3.2, 3.6**

Property 7: Preservation - Permanent Uninstall Removal and Non-Full Drag Insertion

_For any_ app whose .desktop file has been absent for N or more consecutive scans
(permanent uninstall), the fixed `apply_scan_results` SHALL remove the app and
compact the grid exactly as the original code did. _For any_ drag to a target page
with fewer than page_size items (where the dragged item is not already present),
the fixed `_reorder_main` SHALL insert the item and reassign sort positions within
the page's slot range exactly as the original code did.

**Validates: Requirements 3.3, 3.4**

Property 8: Preservation - Scalable Precedence and New-App Sort Appending

_For any_ icon path containing "scalable" as a path component, the fixed
`_parse_size` SHALL return 9999 with precedence over any "NxN" directory. _For any_
newly discovered app in scan results, the fixed `apply_scan_results` SHALL add it
with a new identifier appended after the current maximum sort position, exactly as
the original code did.

**Validates: Requirements 3.5, 3.7**

## Fix Implementation

### Fix 1: Null-pixmap guards in icon fallback chain (Bugs 1.1 & 1.2)

**File**: `src/linxpad/ui/components/icon_utils.py`

**Functions**: `app_pixmap()`, `load_app_icon()`

**Specific Changes**:

1. **Guard `make_pixmap` results in `app_pixmap()`**: After every `make_pixmap()`
   call, check `pix.isNull()` before returning. If null, fall through to the next
   branch in the chain.

   ```python
   def app_pixmap(item: dict, size: int, icon_resolver=None) -> QPixmap:
       """Return a QPixmap for an app item (no QLabel needed)."""
       icon_path = item.get("icon")
       icon_name = item.get("icon_name")

       if icon_path and os.path.exists(icon_path):
           pix = make_pixmap(icon_path, size)
           if not pix.isNull():
               return pix
       if icon_name:
           qi = QIcon.fromTheme(icon_name)
           if not qi.isNull():
               return qi.pixmap(size, size)
       if icon_name and icon_resolver:
           resolved = icon_resolver.resolve(icon_name)
           if resolved and os.path.exists(resolved):
               pix = make_pixmap(resolved, size)
               if not pix.isNull():
                   return pix

       return _fallback(size, (item.get("name") or "?")[0].upper())
   ```

   - The `icon_path` branch already checked `os.path.exists`; the added `isNull()`
     guard catches SVG-without-plugin and corrupt-file cases (Bug 1.2).
   - The resolver branch gains both `os.path.exists(resolved)` (catches stale cached
     paths — Bug 1.1) and `isNull()` (catches SVG-without-plugin for resolved paths).
   - The `QIcon.fromTheme` branch already checks `qi.isNull()` — no change needed.

2. **Refactor `load_app_icon()` to delegate to `app_pixmap()`**: Eliminate the
   duplicated fallback chain by calling the fixed `app_pixmap()`.

   ```python
   def load_app_icon(label, item: dict, size: int, icon_resolver=None) -> None:
       """Load an app icon into a QLabel with fallback chain."""
       label.setPixmap(app_pixmap(item, size, icon_resolver))
   ```

   - This ensures `SearchRow` (which calls `load_app_icon`) gets the same
     null-guarded fallback chain as `IconItem._load_pixmap` (which calls
     `app_pixmap` directly).
   - `_fallback()` itself always returns a non-null pixmap (it creates a
     `QPixmap(size, size)` and fills it), so the terminal fallback is safe.

3. **Optional enhancement — cache re-validation in `IconResolver.resolve()`**:
   When a cached path no longer exists on disk, evict the stale entry and re-resolve
   so future renders find a valid alternative (e.g. from a different theme) rather
   than repeatedly hitting the `os.path.exists` guard.

   **File**: `src/linxpad/services/icons.py`

   ```python
   def resolve(self, icon_name: str | None) -> str | None:
       if not icon_name:
           return None
       if icon_name in self._cache:
           cached = self._cache[icon_name]
           if cached is None or os.path.exists(cached):
               return cached
           # Stale cache entry — fall through to re-resolve
       result = self._find(icon_name)
       self._cache[icon_name] = result
       return result
   ```

   - This is a robustness improvement, not strictly required by the requirements
     (the `os.path.exists` guard in `app_pixmap` satisfies Req 2.1–2.3). But it
     prevents permanently stale cache entries from masking valid icons installed
     by a replacement theme.

### Fix 2: Grace period for transient .desktop absence (Bug 1.3)

**File**: `src/linxpad/core/launcher_state.py`

**Function**: `LauncherState.__init__()`, `LauncherState.apply_scan_results()`

**Specific Changes**:

1. **Add absence tracking state and configurable grace period to `__init__`**:

   ```python
   def __init__(
       self,
       config: ConfigService,
       scanner: DesktopScanner,
       icons: IconResolver,
       page_size: int = PAGE_SIZE,
       absence_grace: int = 3,
   ):
       self._config = config
       self._scanner = scanner
       self._icons = icons
       self._page_size = page_size
       self._absence_grace = absence_grace
       self._absence_counts: dict[str, int] = {}
       self.apps: dict[str, Application] = {}
       self.folders: dict[str, Folder] = {}
   ```

   - `_absence_counts` is transient (not persisted via `save()`/`load()`). On
     restart, all counts reset to zero. This is acceptable: the grace period
     protects against transient absence within a running session.
   - `absence_grace` defaults to 3 per Req 2.5. The constructor parameter makes it
     configurable; the caller in `main.py` can pass a different value if desired.
   - Existing callers (`LauncherState(cfg, scanner, icons)` in tests, and
     `LauncherState(config, scanner, icons, page_size=...)` in `main.py`) use the
     default of 3 — no call-site changes required.

2. **Modify `apply_scan_results()` to use the grace period**:

   ```python
   def apply_scan_results(self, found: list[dict]) -> bool:
       """Merge scan results into current state. Returns True if changed."""
       found_keys = {(a["name"], a["exec"]) for a in found}
       managed_keys = {(a.name, a.exec): k for k, a in self.apps.items()}
       changed = False

       for key, app_id in list(managed_keys.items()):
           if key not in found_keys:
               self._absence_counts[app_id] = self._absence_counts.get(app_id, 0) + 1
               if self._absence_counts[app_id] >= self._absence_grace:
                   self._compact_page_of(self.apps[app_id].sort_id)
                   del self.apps[app_id]
                   self._absence_counts.pop(app_id, None)
                   changed = True
           else:
               # App present — reset absence count
               self._absence_counts.pop(app_id, None)

       max_sort = max((a.sort_id for a in self.apps.values()), default=-1)
       max_sort = max(max_sort, max((f.sort_id for f in self.folders.values()), default=-1))
       for info in found:
           key = (info["name"], info["exec"])
           if key not in managed_keys:
               app_id = str(uuid.uuid4())
               max_sort += 1
               self.apps[app_id] = Application(
                   id=app_id,
                   name=info["name"],
                   exec=info["exec"],
                   icon=info.get("icon"),
                   icon_name=info.get("icon_name"),
                   comment=info.get("comment"),
                   sort_id=max_sort,
               )
               changed = True

       for app in self.apps.values():
           if app.icon_name:
               resolved = self._icons.resolve(app.icon_name)
               if resolved and resolved != app.icon:
                   app.icon = resolved
                   changed = True

       if changed:
           self.save()
       return changed
   ```

   - The "add new apps" loop is unchanged: it checks `if key not in managed_keys`,
     and absent-within-grace apps are still in `managed_keys` (still in `self.apps`),
     so they are not re-added. When the .desktop reappears, `key in found_keys` is
     True, the count resets, and the app retains its original UUID and sort_id.
   - `changed` remains False when an app is absent but within the grace period
     (no removal, no addition), so `save()` is not called unnecessarily.
   - The `_absence_counts.pop(app_id, None)` on reappearance ensures the count
     resets to zero (absent from the dict = default 0).

### Fix 3: Full-page drag capacity check (Bug 1.4)

**File**: `src/linxpad/core/launcher_state.py`

**Function**: `LauncherState._reorder_main()`

**Specific Changes**:

1. **Change `>` to `>=` in the cross-page capacity check**:

   ```python
   # In _reorder_main(), the cross-page branch:
   if dragged_id in page_ids:
       page_ids.remove(dragged_id)
   else:
       # Dragged from a different page: block if target page is already full
       if len(page_ids) >= self._page_size:   # was: > self._page_size
           return
       self._compact_page_of(dragged_obj.sort_id)
   ```

   - When `len(page_ids) == page_size` (exactly full), `>= page_size` is True, the
     move is blocked, and the function returns without modifying any sort positions.
   - When `len(page_ids) < page_size` (room available), the check is False and the
     move proceeds exactly as before (Req 3.4).
   - The within-page case (`dragged_id in page_ids`) is unaffected: removing the
     dragged item from `page_ids` before reinserting keeps the total count the same.

### Fix 4: NxN size parser (Bug 1.5)

**File**: `src/linxpad/services/icons.py`

**Function**: `IconResolver._parse_size()`

**Specific Changes**:

1. **Validate both sides of "x" are digits with equal values**:

   ```python
   @staticmethod
   def _parse_size(path: str) -> int:
       parts = path.split(os.sep)
       if "scalable" in parts:
           return 9999
       for p in parts:
           if "x" in p:
               halves = p.split("x")
               if len(halves) == 2 and halves[0].isdigit() and halves[1].isdigit():
                   a, b = int(halves[0]), int(halves[1])
                   if a == b:
                       return a
           elif p.isdigit():
               return int(p)
       return 0
   ```

   - For "2x-retina": `split("x")` gives `["2", "-retina"]`. `"-retina".isdigit()`
     is False → condition fails → skip this component, continue scanning. (Req 2.10)
   - For "48x48": `split("x")` gives `["48", "48"]`. Both `isdigit()`, `48 == 48`
     → return 48. (Req 2.9)
   - For "1024x768": both digits but `1024 != 768` → not NxN → skip. This is correct
     per Req 2.9 which requires "equal value". Non-square resolution components are
     not treated as size directories.
   - The `elif p.isdigit()` branch handles pure-numeric components like "48" (some
     themes use bare numbers as directory names). This branch is unchanged.
   - The "scalable" check remains first and unchanged (Req 3.5).

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples
that demonstrate each bug on unfixed code, then verify the fix works correctly and
preserves existing behavior. The project uses `pytest` with `pytest-qt` (headless
via `QT_QPA_PLATFORM=offscreen`). Tests live in `tests/` and follow the existing
convention of class-based test groups with descriptive method names.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate each bug BEFORE implementing the
fix. Confirm or refute the root cause analysis. If we refute, we will need to
re-hypothesize.

**Test Plan**: Write tests that exercise each bug condition on the UNFIXED code to
observe failures and understand the root cause.

**Test Cases**:

1. **Stale Path Test** (Bug 1.1): Create an item dict with an `icon_name` and a
   mock `IconResolver` whose `resolve()` returns a path that does not exist. Call
   `app_pixmap(item, 48, resolver)`. Assert `result.isNull()` is True on unfixed
   code. (Will fail on unfixed code — returns null instead of fallback.)

2. **SVG Null Test** (Bug 1.2): Create an item dict with `icon` pointing to a
   `.svg` file that exists but cannot be loaded (simulate by pointing to a real
   non-image file, or mock `QPixmap` to return null). Call `app_pixmap(item, 48)`.
   Assert `result.isNull()` is True on unfixed code. (Will fail on unfixed code.)

3. **Transient Absence Test** (Bug 1.3): Create a `LauncherState` with one app.
   Call `apply_scan_results([])` once (simulating a single absent scan). Assert the
   app is still present on unfixed code — it will NOT be (bug: immediate removal).
   (Will fail on unfixed code — app is deleted immediately.)

4. **Full Page Drag Test** (Bug 1.4): Create a `LauncherState` with exactly
   `page_size` apps on page 0 and one app on page 1. Call
   `state.reorder(page1_app, page0_app, "before", False, None)`. Assert no sort
   position exceeds page 0's slot range on unfixed code — it WILL exceed. (Will fail
   on unfixed code — overflow into page 1.)

5. **Size Misparse Test** (Bug 1.5): Call `IconResolver._parse_size()` with a path
   containing "2x-retina" before "48x48". Assert the result is 48. On unfixed code
   it returns 2. (Will fail on unfixed code.)

**Expected Counterexamples**:
- Stale path: null pixmap returned where a letter-avatar is expected
- SVG null: null pixmap returned where a letter-avatar is expected
- Transient absence: app deleted on first absence where retention is expected
- Full page drag: sort_id overflows page boundary where block is expected
- Size misparse: returns 2 (from "2x-retina") where 48 (from "48x48") or 0 is expected

### Fix Checking

**Goal**: Verify that for all inputs where each bug condition holds, the fixed
function produces the expected behavior.

**Pseudocode:**
```
// Bug 1.1 & 1.2 — non-null pixmap
FOR ALL item WHERE isBugCondition_stale_path(item, resolver)
            OR isBugCondition_svg_null(item, resolver) DO
  result := app_pixmap_fixed(item, 48, resolver)
  ASSERT NOT result.isNull()
  ASSERT result depicts letter_avatar(item.get("name"))
END FOR

// Bug 1.3 — grace period retention
FOR ALL state, found WHERE isBugCondition_transient_absence(state, found) DO
  state_fixed := apply_scan_results_fixed(state, found)
  FOR EACH absent_app DO
    ASSERT absent_app.id IN state_fixed.apps
    ASSERT absent_app.sort_id UNCHANGED
    ASSERT absence_count(absent_app.id) < N
  END FOR
END FOR

// Bug 1.4 — blocked drag
FOR ALL state, dragged_id, target_id WHERE isBugCondition_full_page_drag(state, dragged_id, target_id) DO
  state_before := copy(state)
  state.reorder_fixed(dragged_id, target_id, "before", False, None)
  ASSERT state.sort_ids == state_before.sort_ids  // no change
END FOR

// Bug 1.5 — correct NxN parsing
FOR ALL path WHERE isBugCondition_size_misparse(path) DO
  result := _parse_size_fixed(path)
  ASSERT result == expected_size(path)  // 0 if no NxN, or N from NxN directory
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the
fixed function produces the same result as the original function.

**Pseudocode:**
```
// Icon rendering preservation (Bugs 1.1 & 1.2)
FOR ALL item WHERE NOT isBugCondition_stale_path(item, resolver)
            AND NOT isBugCondition_svg_null(item, resolver) DO
  ASSERT app_pixmap_original(item, 48, resolver).isNull()
       == app_pixmap_fixed(item, 48, resolver).isNull()
END FOR

// Permanent uninstall preservation (Bug 1.3)
FOR ALL state, found WHERE all absent apps have absence_count >= N DO
  state_orig := apply_scan_results_original(copy(state), found)
  state_fixed := apply_scan_results_fixed(copy(state), found)
  ASSERT set(state_orig.apps.keys()) == set(state_fixed.apps.keys())
END FOR

// Non-full drag preservation (Bug 1.4)
FOR ALL state, dragged_id, target_id WHERE target_page_count < page_size DO
  state_orig := reorder_original(copy(state), ...)
  state_fixed := reorder_fixed(copy(state), ...)
  ASSERT state_orig.sort_ids == state_fixed.sort_ids
END FOR

// Scalable and valid NxN preservation (Bug 1.5)
FOR ALL path WHERE "scalable" IN path OR path has valid NxN component DO
  ASSERT _parse_size_original(path) == _parse_size_fixed(path)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking
because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for valid inputs, then write
property-based tests capturing that behavior.

**Test Cases**:
1. **Valid Icon Path Preservation**: Observe that `app_pixmap` with a valid PNG path
   returns a non-null pixmap on unfixed code, then write a test verifying this
   continues after fix.
2. **QIcon.fromTheme Preservation**: Observe that theme icon lookup works on unfixed
   code, then verify it still works (this branch was not changed).
3. **Letter-Avatar Preservation**: Observe that items with no icon path/name render
   the letter-avatar on unfixed code, then verify this continues.
4. **Permanent Uninstall Preservation**: Observe that apps absent for N+ scans are
   removed on unfixed code, then verify the fixed code also removes them (after
   N scans).
5. **Non-Full Drag Preservation**: Observe that drags to non-full pages succeed on
   unfixed code, then verify the fixed code also succeeds with the same sort_ids.
6. **Scalable Size Preservation**: Observe that "scalable" paths return 9999 on
   unfixed code, then verify this continues.
7. **Valid NxN Preservation**: Observe that "48x48" paths return 48 on unfixed code,
   then verify this continues.
8. **New-App Sort Preservation**: Observe that new apps are appended at max_sort+1
   on unfixed code, then verify this continues.

### Unit Tests

**File**: `tests/test_icon_utils.py` (new)

- `test_app_pixmap_valid_png_returns_non_null`: valid PNG path → non-null pixmap
- `test_app_pixmap_stale_path_returns_fallback`: resolver returns non-existent path
  → non-null letter-avatar pixmap
- `test_app_pixmap_missing_file_returns_fallback`: icon_path doesn't exist → fallback
- `test_app_pixmap_null_pixmap_falls_through`: mock make_pixmap to return null →
  fallback
- `test_app_pixmap_no_icon_no_name_returns_fallback`: no icon, no icon_name → fallback
- `test_app_pixmap_empty_name_returns_question_mark`: name="" → fallback draws "?"
- `test_load_app_icon_delegates_to_app_pixmap`: verify load_app_icon sets the same
  pixmap as app_pixmap returns
- `test_folder_collage_uses_fallback_for_broken_children`: child with broken icon →
  collage shows letter-avatar for that child

**File**: `tests/test_icon_size.py` (new, or add to existing test structure)

- `test_parse_size_nxn_48x48`: returns 48
- `test_parse_size_nxn_16x16`: returns 16
- `test_parse_size_2x_retina_skipped`: "2x-retina" → 0 (no NxN after it)
- `test_parse_size_2x_retina_then_48x48`: returns 48 (skips "2x-retina")
- `test_parse_size_scalable_returns_9999`: "scalable" → 9999
- `test_parse_size_scalable_overrides_nxn`: "scalable/48x48" → 9999
- `test_parse_size_pure_digit`: "48" → 48
- `test_parse_size_no_size_component`: "apps/firefox.png" → 0
- `test_parse_size_non_equal_nxn_skipped`: "1024x768" → 0 (not equal, not NxN)

**File**: `tests/test_launcher_state.py` (extend existing)

- `test_apply_scan_retains_app_within_grace_period`: absent 1 scan → retained
- `test_apply_scan_retains_app_for_grace_minus_one`: absent N-1 scans → retained
- `test_apply_scan_removes_after_grace_period`: absent N scans → removed
- `test_apply_scan_resets_count_on_reappearance`: absent 1, present 1 → count 0
- `test_apply_scan_preserves_sort_id_during_grace`: absent within grace → sort_id
  unchanged
- `test_apply_scan_preserves_folder_membership_during_grace`: absent within grace →
  folder_id unchanged
- `test_apply_scan_permanent_uninstall_removed_after_grace`: absent N+1 → removed
- `test_reorder_blocks_drag_to_full_page`: page_size items on target → blocked
- `test_reorder_blocks_drag_to_exactly_full_page`: exactly page_size → blocked
- `test_reorder_allows_drag_to_non_full_page`: page_size - 1 items → succeeds
- `test_reorder_within_page_unaffected`: within-page reorder → same as before
- `test_reorder_no_sort_overflow_after_block`: blocked drag → no sort_id exceeds
  page boundary

### Property-Based Tests

- **Non-null pixmap property**: Generate random app items with varied icon paths
  (valid, non-existent, .svg, .svgz, None, empty string) and icon names (valid,
  invalid, None). Assert `app_pixmap` NEVER returns a null pixmap for any input.
- **Fallback identity property**: Generate items with no valid icon. Assert the
  fallback pixmap's first character matches `item["name"][0].upper()` (or "?" for
  empty/missing names).
- **Grace period property**: Generate random scan sequences (present/absent) for
  an app. Assert the app is retained iff no run of N consecutive absences occurs;
  assert UUID and sort_id are unchanged while retained.
- **Count reset property**: Generate random interleavings of present/absent scans.
  Assert any present scan resets the absence counter to 0.
- **Full-page block property**: Generate random page configurations with page_size
  items on the target page. Assert cross-page drag produces no sort_id changes.
- **Non-full page insert property**: Generate random page configurations with
  < page_size items. Assert cross-page drag succeeds and all sort_ids are within
  the target page's slot range.
- **NxN parsing property**: Generate random paths with varied "x" components
  (NxN, Nx-non-digit, NxN@2x, pure-digit, "scalable"). Assert the parser returns
  the correct size: 9999 for scalable, N for NxN, 0 when no valid size found.
- **Size parser preservation property**: Generate random paths containing "scalable"
  or valid "NxN" components. Assert `_parse_size` returns the same value as the
  original implementation.

### Integration Tests

- **Full icon pipeline**: Create a temp directory with real .desktop files and
  icon files (PNG and SVG). Run `DesktopScanner.scan()` → `LauncherState.apply_scan_results()`
  → `app_pixmap()` for each app. Assert all pixmaps are non-null.
- **Theme uninstall simulation**: Set up icons, resolve them (populating cache),
  delete the icon files (simulating theme uninstall), re-render. Assert all
  pixmaps are non-null (letter-avatar fallback).
- **SVG plugin unavailable**: Create .svg icon files, mock `QPixmap` to return null
  for SVG paths. Assert `app_pixmap` returns letter-avatar for SVG items.
- **Package update flow**: Create a .desktop file, scan, then temporarily remove it,
  scan again (within grace period), assert app retained. Scan N times, assert
  removed. Re-add file before N, assert app preserved with original UUID/sort_id.
- **Cross-page drag full flow**: Fill a page to capacity, drag from another page,
  assert the drag is blocked and the grid layout is unchanged. Drag to a non-full
  page, assert insertion succeeds.
- **Size selection end-to-end**: Create icon paths with "2x-retina" and "48x48"
  components. Run `IconResolver._find()` and assert the correct-sized icon is
  selected (largest NxN wins, "2x-retina" ignored).
