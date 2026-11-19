# Phase 1 Report — Bug Condition Tests C1–C5

## Test run summary

Run command:
```
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_icon_utils.py tests/test_launcher_state.py tests/test_icons.py -v
```

Result: **5 failed, 12 passed** (17 total collected)

---

## C1 — Stale cached path (Bug 1.1)

**test**: `tests/test_icon_utils.py::test_c1_stale_cached_path`
**Status**: FAILED ✓ (expected — confirms bug exists)

**Failure message**:
```
AssertionError: Expected non-null letter-avatar pixmap, got null.
Bug 1.1: resolver returns stale non-existent path, app_pixmap returns null.
assert not True
 +  where True = <built-in method isNull of QPixmap object at 0x...>()
```

**What this proves**: `app_pixmap` calls `make_pixmap(resolved, size)` without first checking `os.path.exists(resolved)`. When the resolver returns a path that no longer exists on disk, `QPixmap(path)` returns a null pixmap and `app_pixmap` returns it directly instead of falling through to the letter-avatar fallback.

---

## C2 — SVG without plugin (Bug 1.2)

**test**: `tests/test_icon_utils.py::test_c2_svg_without_plugin`
**Status**: PASSED (unexpected — bug not triggered in this environment)

**Explanation**: The Qt SVG plugin is present on this system, so `QPixmap(svg_path)` successfully loads the SVG and returns a non-null pixmap. The test passed because the existing path branch returns a valid pixmap. The bug (returning null when the SVG plugin is absent) requires an environment without the Qt SVG plugin. The test correctly captures the expected behavior post-fix; it passes here because the environment condition for the bug is not met.

---

## C3 — Transient absence (Bug 1.3)

**test**: `tests/test_launcher_state.py::test_c3_transient_absence`
**Status**: FAILED ✓ (expected — confirms bug exists)

**Failure message**:
```
AssertionError: App should survive first empty scan (transient absence).
Bug 1.3: app deleted immediately on first empty scan.
assert 'abc-123' in {}
 +  where {} = <linxpad.core.launcher_state.LauncherState object at 0x...>.apps
```

**What this proves**: `apply_scan_results([])` with one existing app deletes it on the first empty scan. There is no grace period. The app is gone after a single call with an empty found list.

---

## C4 — Full-page drag overflow (Bug 1.4)

**test**: `tests/test_launcher_state.py::test_c4_full_page_drag_overflow`
**Status**: FAILED ✓ (expected — confirms bug exists)

**Failure message**:
```
AssertionError: Dragged item x50 sort_id should remain 48 (page 0 is full), got 5.
Bug 1.4: reorder allowed overflow onto full page.
assert 5 == 48
 +  where 5 = Application(id='x50', ..., sort_id=5, ...).sort_id
```

**What this proves**: `_reorder_main` uses `if len(page_ids) > self._page_size:` to guard against dragging onto a full page. When the target page has exactly `page_size` (24) items, `24 > 24` is False and the guard does not fire, so the drag proceeds. This inserts the dragged item into the full page, causing sort_ids to overflow into the next page's slot range.

---

## C5a — Size misparse: retina dir (Bug 1.5)

**test**: `tests/test_icons.py::test_c5_size_misparse_retina_dir`
**Status**: FAILED ✓ (expected — confirms bug exists)

**Failure message**:
```
AssertionError: Expected 0 for path with '2x-retina' dir (no NxN component), got 2.
Bug 1.5: _parse_size misparses '2x-retina' as size 2.
assert 2 == 0
```

**What this proves**: `_parse_size` splits each path component on `"x"` and checks whether the left side is a digit. For `"2x-retina"`, `"2x-retina".split("x")[0]` is `"2"`, which `.isdigit()` returns True, so it returns `int("2") = 2`. The right side `"-retina"` is never checked.

---

## C5b — Size misparse: valid NxN shadowed (Bug 1.5 extended)

**test**: `tests/test_icons.py::test_c5_size_parse_valid_nxn`
**Status**: FAILED (unexpected — bug is broader than anticipated)

**Failure message**:
```
AssertionError: Expected 48 for path with '48x48' dir, got 2.
Bug 1.5: _parse_size failed to find 48.
assert 2 == 48
```

**What this proves**: The bug is worse than the task description indicated. When the path contains both `2x-retina` and `48x48`, the parser hits `2x-retina` first, misparses it as size 2, and returns immediately — `48x48` is never reached. The fix must not only reject `2x-retina` but also continue scanning subsequent components to find the correct `48x48`.

---

## Summary table

| Test | Bug | Expected | Actual | Notes |
|------|-----|----------|--------|-------|
| test_c1_stale_cached_path | 1.1 | FAIL | FAIL ✓ | Bug confirmed |
| test_c2_svg_without_plugin | 1.2 | FAIL | PASS | Qt SVG plugin present; bug not triggered |
| test_c3_transient_absence | 1.3 | FAIL | FAIL ✓ | Bug confirmed |
| test_c4_full_page_drag_overflow | 1.4 | FAIL | FAIL ✓ | Bug confirmed |
| test_c5_size_misparse_retina_dir | 1.5 | FAIL | FAIL ✓ | Bug confirmed |
| test_c5_size_parse_valid_nxn | 1.5 | PASS | FAIL | Bug is broader: `2x-retina` shadows `48x48` |
