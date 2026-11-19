# Implementation Plan

## Overview

This plan fixes five icon-disappearance defects in LinxPad using the exploratory bugfix workflow. Tasks are ordered in four phases:

1. **Bug Condition Exploration Tests (tasks 1–4)** — written BEFORE any fix, run on unfixed code, expected to FAIL to confirm each bug exists.
2. **Preservation Property Tests (tasks 5–7)** — written BEFORE any fix, run on unfixed code, expected to PASS to establish the behavioral baseline.
3. **Implementation (tasks 8–12)** — surgical fixes across `icon_utils.py`, `launcher_state.py`, and `icons.py`; re-runs exploration tests (which should now PASS) and preservation tests (which must still PASS).
4. **Checkpoint (task 13)** — full test suite and linter run to confirm all bugs are resolved with no regressions.

Bugs addressed: stale cached icon path (1.1), SVG without Qt plugin (1.2), transient `.desktop` absence (1.3), full-page drag overflow (1.4), icon size misparse (1.5).

## Tasks

### Prerequisites

- [x] 0. Add hypothesis to dev dependencies for property-based testing
  - Add `hypothesis>=6.0` to `[project.optional-dependencies] dev` list in `pyproject.toml`
  - Add `hypothesis>=6.0` to `requirements-dev.txt` under the Testing section
  - Run `pip install -e ".[dev]"` to install
  - Verify: `python3 -c "import hypothesis; print(hypothesis.__version__)"`
  - The design document specifies property-based tests for preservation checking that require hypothesis to generate many test cases automatically

### Phase 1: Bug Condition Exploration Tests

_Write these tests BEFORE implementing any fix. Each test MUST FAIL on unfixed code — failure confirms the bug exists. Do NOT fix the test or the code when it fails._

- [x] 1. Write bug condition exploration test: stale path & SVG null pixmap (Bugs 1.1 & 1.2)
  - **Property 1: Bug Condition** - Non-Null Pixmap Fallback for Stale and SVG Paths
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope to concrete failing cases for reproducibility
  - **Test file**: `tests/test_icon_utils.py` (new)
  - **C₁ — Stale cached path (Bug 1.1)**: Create an item dict with `icon_name="firefox"` and a mock `IconResolver` whose `resolve()` returns a path that does not exist on disk (e.g. `"/nonexistent/icons/firefox.png"`). Call `app_pixmap(item, 48, resolver)`. Assert `result.isNull()` is False and the pixmap depicts the letter-avatar "F" (from app name "Firefox"). On unfixed code, `app_pixmap` returns a null pixmap because the resolver branch checks only `if resolved:` (truthy for any non-None string) without `os.path.exists()`, so `make_pixmap` returns null.
  - **C₂ — SVG without plugin (Bug 1.2)**: Create an item dict with `icon` pointing to a `.svg` file that exists on disk but cannot be loaded as a pixmap (simulate by writing a minimal text file with `.svg` extension, or mock `QPixmap` to return null for the path). Call `app_pixmap(item, 48)`. Assert `result.isNull()` is False and the pixmap depicts the letter-avatar. On unfixed code, `app_pixmap` calls `make_pixmap(icon_path, size)` and returns the result directly without checking `.isNull()`, so the null SVG pixmap is returned.
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found: "app_pixmap with stale resolver path returns null pixmap instead of letter-avatar", "app_pixmap with SVG path that yields null QPixmap returns null instead of letter-avatar"
  - Mark task complete when tests are written, run, and failure is documented
  - _Bug_Condition: isBugCondition_stale_path(item, icon_resolver) OR isBugCondition_svg_null(item, icon_resolver) from design_
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2. Write bug condition exploration test: transient .desktop absence (Bug 1.3)
  - **Property 1: Bug Condition** - Grace Period Retention for Transient .desktop Absence
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope to concrete failing cases for reproducibility
  - **Test file**: `tests/test_launcher_state.py` (extend)
  - **C₃ — Transient absence**: Create a `LauncherState` with one app (UUID "abc-123", sort_id=5, name="Firefox", exec="firefox.desktop"). Call `apply_scan_results([])` once (simulating a single absent scan). Assert the app is still present in `state.apps` with the same UUID and sort_id. On unfixed code, the app is deleted immediately because `apply_scan_results` calls `del self.apps[app_id]` for any key not in `found_keys` without a grace period.
  - Also test: call `apply_scan_results([])` a second time (count=2, still < N=3). Assert app still present. On unfixed code, app already deleted after first scan.
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists)
  - Document counterexample: "apply_scan_results([]) with one existing app deletes the app on first absence instead of retaining it for grace period of 3"
  - Mark task complete when test is written, run, and failure is documented
  - _Bug_Condition: isBugCondition_transient_absence(state, found) from design_
  - _Requirements: 2.5, 2.7_

- [x] 3. Write bug condition exploration test: full-page drag overflow (Bug 1.4)
  - **Property 1: Bug Condition** - Block Drag to Full Page
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope to concrete failing case: target page has exactly page_size items
  - **Test file**: `tests/test_launcher_state.py` (extend)
  - **C₄ — Full-page drag**: Create a `LauncherState` with exactly `page_size` (24) apps on page 0 (sort_ids 0–23) and one app "x50" on page 2 (sort_id=48). Call `state.reorder("x50", "x05", "before", False, None)` — dragging x50 onto page 0 which is exactly full. Assert no item's sort_id exceeds page 0's slot range (0–23) and the dragged item remains at sort_id=48. On unfixed code, `len(page_ids) > self._page_size` evaluates to `24 > 24` = False, so the move proceeds and a sort position overflows past page 0's slot range into page 1's slots.
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists)
  - Document counterexample: "reorder with target page having exactly page_size items proceeds because `len(page_ids) > page_size` is False for `==` case, causing sort_id overflow into next page"
  - Mark task complete when test is written, run, and failure is documented
  - _Bug_Condition: isBugCondition_full_page_drag(state, dragged_id, target_id) from design_
  - _Requirements: 2.8_

- [x] 4. Write bug condition exploration test: icon size misparse (Bug 1.5)
  - **Property 1: Bug Condition** - Correct NxN Size Parsing
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope to concrete failing cases for reproducibility
  - **Test file**: `tests/test_icons.py` (new)
  - **C₅ — Size misparse**: Call `IconResolver._parse_size("/usr/share/icons/Adwaita/2x-retina/apps/firefox.png")`. Assert result is 0 (no valid NxN directory present). On unfixed code, returns 2 because `p.split("x")[0]` = "2", `"2".isdigit()` is True, and the parser returns `int("2")` without checking that the part after "x" is also digits.
  - Also test: `IconResolver._parse_size("/usr/share/icons/Adwaita/2x-retina/48x48/apps/firefox.png")`. Assert result is 48 (skip "2x-retina", find "48x48"). On unfixed code, returns 2.
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists)
  - Document counterexamples: "_parse_size('...2x-retina/apps/...') returns 2 instead of 0", "_parse_size('...2x-retina/48x48/apps/...') returns 2 instead of 48"
  - Mark task complete when test is written, run, and failure is documented
  - _Bug_Condition: isBugCondition_size_misparse(path) from design_
  - _Requirements: 2.9, 2.10_

### Phase 2: Preservation Property Tests

_Write these tests BEFORE implementing any fix. Observe behavior on UNFIXED code for non-buggy inputs, then write tests that capture that behavior. These tests MUST PASS on unfixed code — they confirm the baseline behavior to preserve._

- [ ] 5. Write preservation property tests: valid icon and SVG rendering (Bugs 1.1 & 1.2)
  - **Property 2: Preservation** - Valid Icon and SVG Rendering
  - **IMPORTANT**: Follow observation-first methodology
  - **Test file**: `tests/test_icon_utils.py` (new)
  - Observe on UNFIXED code: `app_pixmap` with a valid PNG path (file exists, non-null pixmap) returns a non-null pixmap
  - Observe on UNFIXED code: `app_pixmap` with an item having no icon path and no icon name returns the letter-avatar fallback (non-null pixmap)
  - Observe on UNFIXED code: `app_pixmap` with `icon_name` resolving via `QIcon.fromTheme` to a valid theme icon returns that icon's pixmap (this branch already checks `qi.isNull()` and is correct)
  - Write property-based test using hypothesis: for any app item where the bug condition does NOT hold (stored icon path exists and yields non-null pixmap, OR app has neither valid path nor resolvable name), `app_pixmap` SHALL produce a non-null pixmap. Generate random app items with varied icon configurations: valid PNG paths, None icon paths, valid icon names, empty names. Assert `not result.isNull()` for all.
  - Write test: `app_pixmap` with valid PNG path returns non-null pixmap (Req 3.1)
  - Write test: `app_pixmap` with `icon_name` that resolves via `QIcon.fromTheme` returns the theme icon's pixmap (non-null) (Req 3.1)
  - Write test: `app_pixmap` with no icon path and no icon name returns letter-avatar fallback (non-null) (Req 3.6)
  - Write test: `app_pixmap` with empty name string returns letter-avatar with "?" (Req 3.6)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.6_

- [ ] 6. Write preservation property tests: launcher state behavior (Bugs 1.3 & 1.4)
  - **Property 2: Preservation** - Permanent Uninstall Removal and Non-Full Drag Insertion
  - **IMPORTANT**: Follow observation-first methodology
  - **Test file**: `tests/test_launcher_state.py` (extend)
  - Observe on UNFIXED code: `apply_scan_results([])` with one existing app removes the app (current behavior — permanent uninstall). The fixed code should also remove after N consecutive absences. Write test verifying app is removed after N+ absences (Req 3.3).
  - Observe on UNFIXED code: `reorder` with target page having fewer than `page_size` items succeeds and reassigns sort positions within the page's slot range. Write test verifying all sort_ids stay within target page range (Req 3.4).
  - Observe on UNFIXED code: `apply_scan_results` with new apps appends them at `max_sort + 1`. Write test verifying new apps get sort_id = max_sort + 1 (Req 3.7).
  - Write property-based test using hypothesis: for any scan sequence where an app is absent for N or more consecutive scans, the app SHALL be removed from state. Generate random scan sequences (present/absent) and assert removal occurs iff a run of N consecutive absences occurs.
  - Write property-based test using hypothesis: for any drag to a target page with fewer than `page_size` items (where dragged item is not already present), the reorder SHALL succeed and all sort_ids on the target page SHALL be within the page's slot range. Generate random page configurations with < page_size items.
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.3, 3.4, 3.7_

- [ ] 7. Write preservation property tests: size parser behavior (Bug 1.5)
  - **Property 2: Preservation** - Scalable Precedence and Valid NxN Parsing
  - **IMPORTANT**: Follow observation-first methodology
  - **Test file**: `tests/test_icons.py` (new)
  - Observe on UNFIXED code: `IconResolver._parse_size` with "scalable" in path returns 9999. Write test verifying this (Req 3.5).
  - Observe on UNFIXED code: `IconResolver._parse_size` with "scalable/48x48" in path returns 9999 (scalable takes precedence). Write test verifying this (Req 3.5).
  - Observe on UNFIXED code: `IconResolver._parse_size` with "48x48" in path returns 48. Write test verifying this (valid NxN preserved).
  - Observe on UNFIXED code: `IconResolver._parse_size` with "16x16" in path returns 16. Write test verifying this.
  - Observe on UNFIXED code: `IconResolver._parse_size` with "48" (pure digit) in path returns 48. Write test verifying this (pure-numeric component preserved).
  - Write property-based test using hypothesis: for any path containing "scalable" or a valid "NxN" component, `_parse_size` SHALL return the same value as the original implementation. Generate random paths with varied components (scalable, NxN, pure-digit, non-size strings).
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.5_

### Phase 3: Implementation

- [ ] 8. Fix 1: Null-pixmap guards in icon fallback chain (Bugs 1.1 & 1.2)

  - [ ] 8.1 Implement the fix in `app_pixmap()` and `load_app_icon()`
    - **File**: `src/linxpad/ui/components/icon_utils.py`
    - **`app_pixmap()` changes**:
      - In the `icon_path` branch: after `make_pixmap(icon_path, size)`, check `pix.isNull()` before returning. If null, fall through to next branch. This catches SVG-without-plugin and corrupt-file cases (Bug 1.2).
      - In the resolver branch: add `os.path.exists(resolved)` check before calling `make_pixmap(resolved, size)`. This catches stale cached paths (Bug 1.1). Also check `pix.isNull()` after `make_pixmap` in this branch.
      - The `QIcon.fromTheme(icon_name)` branch already checks `qi.isNull()` — no change needed.
      - The `_fallback()` terminal branch always returns a non-null pixmap — no change needed.
    - **`load_app_icon()` changes**: Refactor to delegate to `app_pixmap()` — replace the duplicated fallback chain with `label.setPixmap(app_pixmap(item, size, icon_resolver))`. This ensures `SearchRow` gets the same null-guarded chain as `IconItem._load_pixmap`.
    - Verify `_fallback()` always returns non-null (it creates `QPixmap(size, size)` and fills it — safe by construction)
    - _Bug_Condition: isBugCondition_stale_path(item, icon_resolver) where resolver returns cached path whose file no longer exists; isBugCondition_svg_null(item, icon_resolver) where .svg/.svgz path yields null QPixmap_
    - _Expected_Behavior: app_pixmap returns non-null QPixmap (letter-avatar fallback drawn from uppercased first character of app name, or "?" when empty) for all items satisfying bug condition — from design Property 1_
    - _Preservation: valid icon paths (file exists, non-null pixmap) render unchanged; SVG with plugin available renders unchanged; no-icon items render letter-avatar unchanged — from design Property 6_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.6_

  - [ ] 8.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Non-Null Pixmap Fallback for Stale and SVG Paths
    - **IMPORTANT**: Re-run the SAME tests from task 1 — do NOT write new tests
    - The tests from task 1 encode the expected behavior
    - When these tests pass, it confirms the expected behavior is satisfied
    - Run bug condition exploration tests from task 1 (stale path & SVG null)
    - **EXPECTED OUTCOME**: Tests PASS (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 8.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Valid Icon and SVG Rendering
    - **IMPORTANT**: Re-run the SAME tests from task 5 — do NOT write new tests
    - Run preservation property tests from task 5 (valid icon rendering, SVG with plugin, letter-avatar)
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.6_

- [ ] 9. Fix 2: Grace period for transient .desktop absence (Bug 1.3)

  - [ ] 9.1 Implement the fix in `LauncherState`
    - **File**: `src/linxpad/core/launcher_state.py`
    - **`__init__()` changes**: Add `absence_grace: int = 3` parameter and `self._absence_counts: dict[str, int] = {}` field. The grace period defaults to 3 per Req 2.5. Existing callers (`LauncherState(cfg, scanner, icons)` and `LauncherState(config, scanner, icons, page_size=...)`) use the default of 3 — no call-site changes required. `_absence_counts` is transient (not persisted via `save()`/`load()`); on restart all counts reset to zero.
    - **`apply_scan_results()` changes**:
      - In the removal loop: when `key not in found_keys`, increment `self._absence_counts[app_id]` by 1. Only remove the app (compact page + `del`) when `self._absence_counts[app_id] >= self._absence_grace`. On removal, also `pop` the absence count.
      - When `key in found_keys`: reset the absence count with `self._absence_counts.pop(app_id, None)` (absent from dict = default 0). This ensures reappearance resets the counter.
      - `changed` remains False when an app is absent but within the grace period (no removal, no addition), so `save()` is not called unnecessarily.
      - The "add new apps" loop is unchanged: absent-within-grace apps are still in `managed_keys` (still in `self.apps`), so they are not re-added. When the .desktop reappears, the app retains its original UUID and sort_id.
    - _Bug_Condition: isBugCondition_transient_absence(state, found) where app is absent from scan results for fewer than N consecutive scans_
    - _Expected_Behavior: apply_scan_results retains app in state with identifier, grid position (sort_id), and folder membership unchanged during grace period; resets consecutive absence count to zero on reappearance — from design Property 2; removes app after N or more consecutive absences — from design Property 3_
    - _Preservation: permanent uninstall (absent for N+ scans) still removes app and compacts grid; new apps still appended at max_sort+1 — from design Properties 7 and 8_
    - _Requirements: 2.5, 2.6, 2.7, 3.3, 3.7_

  - [ ] 9.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Grace Period Retention for Transient .desktop Absence
    - **IMPORTANT**: Re-run the SAME test from task 2 — do NOT write a new test
    - The test from task 2 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from task 2 (transient absence retention)
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.5, 2.7_

  - [ ] 9.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Permanent Uninstall Removal and Non-Full Drag Insertion
    - **IMPORTANT**: Re-run the SAME tests from task 6 — do NOT write new tests
    - Run preservation property tests from task 6 (permanent uninstall removal, non-full drag insertion, new-app sort appending)
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.3, 3.4, 3.7_

- [ ] 10. Fix 3: Full-page drag capacity check (Bug 1.4)

  - [ ] 10.1 Implement the fix in `_reorder_main()`
    - **File**: `src/linxpad/core/launcher_state.py`
    - **`_reorder_main()` changes**: In the cross-page branch (the `else` after `if dragged_id in page_ids:`), change `if len(page_ids) > self._page_size:` to `if len(page_ids) >= self._page_size:`. This is a one-character fix: `>` becomes `>=`.
    - When `len(page_ids) == page_size` (exactly full), `>= page_size` is True, the move is blocked (function returns), and no sort positions are modified.
    - When `len(page_ids) < page_size` (room available), the check is False and the move proceeds exactly as before.
    - The within-page case (`dragged_id in page_ids`) is unaffected: removing the dragged item from `page_ids` before reinserting keeps the total count the same.
    - _Bug_Condition: isBugCondition_full_page_drag(state, dragged_id, target_id) where dragged item not on target page and target page has exactly page_size items_
    - _Expected_Behavior: _reorder_main blocks the move so dragged item remains at original sort position, no item's sort position is modified, grid layout unchanged — from design Property 4_
    - _Preservation: non-full page drags (target page < page_size) still insert item and reassign sort positions within page's slot range — from design Property 7_
    - _Requirements: 2.8, 3.4_

  - [ ] 10.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Block Drag to Full Page
    - **IMPORTANT**: Re-run the SAME test from task 3 — do NOT write a new test
    - The test from task 3 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from task 3 (full-page drag overflow)
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.8_

  - [ ] 10.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Permanent Uninstall Removal and Non-Full Drag Insertion
    - **IMPORTANT**: Re-run the SAME tests from task 6 — do NOT write new tests
    - Run preservation property tests from task 6 (non-full drag insertion)
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.4_

- [ ] 11. Fix 4: NxN size parser (Bug 1.5)

  - [ ] 11.1 Implement the fix in `_parse_size()`
    - **File**: `src/linxpad/services/icons.py`
    - **`_parse_size()` changes**: Replace the `"x" in p` check with a stricter NxN validation:
      - Split `p` on "x" into `halves`.
      - Check `len(halves) == 2 AND halves[0].isdigit() AND halves[1].isdigit()`.
      - If both sides are digits and equal (`int(halves[0]) == int(halves[1])`), return that value.
      - If the sides are not equal (e.g. "1024x768"), skip — not an NxN size directory.
      - If the part after "x" is not purely digits (e.g. "2x-retina" → ["2", "-retina"]), skip — not NxN.
    - The `elif p.isdigit()` branch for pure-numeric components (like "48") remains unchanged.
    - The `"scalable" in parts` check remains first and unchanged (Req 3.5).
    - For "2x-retina": `split("x")` → `["2", "-retina"]`, `"-retina".isdigit()` is False → skip, continue scanning.
    - For "48x48": `split("x")` → `["48", "48"]`, both `isdigit()`, `48 == 48` → return 48.
    - For "1024x768": both digits but `1024 != 768` → skip (not NxN).
    - _Bug_Condition: isBugCondition_size_misparse(path) where path contains component with "x" but part after "x" is not purely digits (e.g. "2x-retina")_
    - _Expected_Behavior: _parse_size returns N for NxN size directory (both sides digits, equal values), ignores non-NxN "x" components — from design Property 5_
    - _Preservation: "scalable" returns 9999 with precedence over NxN; valid NxN components return N; pure-numeric components return their value — from design Property 8_
    - _Requirements: 2.9, 2.10, 3.5_

  - [ ] 11.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Correct NxN Size Parsing
    - **IMPORTANT**: Re-run the SAME test from task 4 — do NOT write a new test
    - The test from task 4 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from task 4 (size misparse)
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.9, 2.10_

  - [ ] 11.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Scalable Precedence and Valid NxN Parsing
    - **IMPORTANT**: Re-run the SAME tests from task 7 — do NOT write new tests
    - Run preservation property tests from task 7 (scalable returns 9999, valid NxN returns N, pure-digit preserved)
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.5_

- [ ] 12. Optional: Cache re-validation in IconResolver.resolve()
  - **File**: `src/linxpad/services/icons.py`
  - **`resolve()` changes**: When a cached path no longer exists on disk, evict the stale entry and re-resolve so future renders find a valid alternative (e.g. from a replacement theme) rather than repeatedly hitting the `os.path.exists` guard in `app_pixmap`.
  - In the cache-hit branch: check `if cached is None or os.path.exists(cached): return cached`. If the cached path no longer exists, fall through to re-resolve via `self._find(icon_name)` and update the cache.
  - This is a robustness improvement, not strictly required by the requirements (the `os.path.exists` guard in `app_pixmap` satisfies Req 2.1–2.3). It prevents permanently stale cache entries from masking valid icons installed by a replacement theme.
  - Write test: `IconResolver.resolve()` with a stale cached path evicts and re-resolves
  - Write test: `IconResolver.resolve()` with a valid cached path returns the cached value without re-resolving
  - _Requirements: 2.1, 2.2, 2.3 (supplementary)_

### Phase 4: Checkpoint

- [ ] 13. Checkpoint - Ensure all tests pass
  - Run full test suite: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v --run`
  - Verify all bug condition exploration tests now PASS (bugs fixed)
  - Verify all preservation property tests still PASS (no regressions)
  - Verify optional cache re-validation tests pass (if implemented)
  - Run linter: `ruff check src/ tests/` and `black --check src/ tests/`
  - Ensure all 5 bugs are resolved: stale path fallback (1.1), SVG null fallback (1.2), grace period retention (1.3), full-page drag block (1.4), NxN size parsing (1.5)
  - Ensure no regressions in existing behavior: valid icon rendering, permanent uninstall removal, non-full drag insertion, scalable precedence, new-app sort appending
  - Ask the user if any questions arise

## Notes

- All exploration tests (tasks 1–4) run against **unfixed** code and are expected to **FAIL** — this is the correct outcome and confirms each bug exists. Do not attempt to fix failing exploration tests; document the counterexamples instead.
- All preservation tests (tasks 5–7) also run against **unfixed** code and are expected to **PASS** — this establishes the behavioral baseline that must not regress.
- After each implementation task (8–11), re-run the corresponding exploration test from Phase 1 (now expected to PASS) and the corresponding preservation test from Phase 2 (must still PASS).
- `_absence_counts` is transient and is not persisted. On process restart all counts reset to zero; the grace period only protects against transient absence within a running session.
- The full-page drag fix (task 10) is a single-character change (`>` → `>=`); verify it does not affect within-page reorders, which remove the dragged item from `page_ids` before reinserting and are unaffected by the cross-page capacity check.
- Property-based tests require `hypothesis>=6.0` (task 0 prerequisite). Run tests headlessly with `QT_QPA_PLATFORM=offscreen` to avoid display requirements in CI.
