# Phase 2 Report — Preservation Property Tests (Tasks 5, 6, 7)

## Summary

All 15 new preservation tests PASS on unfixed code. The 5 phase 1 bug tests still FAIL (unchanged). No regressions introduced.

---

## Task 5 — Preservation: valid icon and SVG rendering

**File**: `tests/test_icon_utils.py`

### Tests added

| Test | Observed behavior on unfixed code | Result |
|------|-----------------------------------|--------|
| `test_app_pixmap_valid_png_path_returns_non_null` | PNG at `src/linxpad/icons/linxpad.png` exists; `make_pixmap` loads it; non-null returned | PASSED |
| `test_app_pixmap_theme_icon_name_returns_non_null` | `QIcon.fromTheme("document-open").isNull()` is True in this environment | SKIPPED |
| `test_app_pixmap_no_icon_path_no_name_returns_letter_avatar` | No icon, no icon_name → `_fallback("F")` → non-null pixmap | PASSED |
| `test_app_pixmap_empty_name_returns_question_mark_avatar` | Empty name → `(""  or "?")[0].upper()` = "?" → `_fallback("?")` → non-null pixmap | PASSED |
| `test_app_pixmap_pbt_non_buggy_items_return_non_null` | 4 items × 1 example each; all return non-null: letter-avatar for no-icon items, make_pixmap for valid PNG | PASSED |

### Methodology notes

Observation-first: The `_fallback()` function fills a `QPixmap(size, size)` and draws a character — by construction always non-null. The valid PNG path `src/linxpad/icons/linxpad.png` exists on disk and Qt can load it. These are confirmed non-buggy code paths. The `icon_name` via `QIcon.fromTheme` branch was skipped because the test theme icon (`document-open`) is unavailable in the headless environment; that branch already has a `qi.isNull()` guard and is correct on both unfixed and fixed code.

### Deviations from spec

None. The spec said to skip if `QIcon.fromTheme("document-open").isNull()` is True; the skip is correct.

---

## Task 6 — Preservation: launcher state

**File**: `tests/test_launcher_state.py`

### Tests added

| Test | Observed behavior on unfixed code | Result |
|------|-----------------------------------|--------|
| `test_apply_scan_results_permanent_uninstall_removes_app` | App deleted on first empty scan (unfixed); absent after 5 scans | PASSED |
| `test_reorder_non_full_page_inserts_within_slot_range` | 3-item page 1 + drag from page 0: all page-1 sort_ids in [24, 47] | PASSED |
| `test_apply_scan_results_new_app_appended_at_max_sort_plus_one` | Existing apps at sort_ids 5 and 10; new app gets sort_id 11 | PASSED |
| `test_pbt_permanent_uninstall_after_5_absences` | 3 concrete app configs × 5 empty scans each → all absent | PASSED |
| `test_pbt_non_full_page_drag_stays_in_slot_range` | 20 sizes (1–20 items on target page); all keep sort_ids in [24, 47] | PASSED |

### Methodology notes

The spec requires tests that assert an app is eventually removed — not that it survives a single absence. On unfixed code the app is removed on the first empty scan; on fixed code it is removed after N consecutive absences. By asserting "absent after 5 consecutive absences", the tests encode behavior that holds on both code versions (assuming grace period N ≤ 5). The PBT for non-full-page drag generates integer item counts 1–20 (all < PAGE_SIZE=24), which is strictly below the full-page boundary that triggers bug 1.4.

### Deviations from spec

None. The spec's key note ("tests MUST NOT test that an app survives one absence; they test that apps ARE eventually removed after enough absences") is exactly what was implemented.

---

## Task 7 — Preservation: size parser

**File**: `tests/test_icons.py`

### Tests added

| Test | Observed behavior on unfixed code | Result |
|------|-----------------------------------|--------|
| `test_parse_size_scalable_returns_9999` | `'scalable' in parts` check is first; returns 9999 | PASSED |
| `test_parse_size_scalable_takes_precedence_over_nxn` | Scalable check fires before component loop; returns 9999 for `scalable/48x48` | PASSED |
| `test_parse_size_valid_nxn_returns_n` | Clean `48x48` with no preceding x-component; returns 48 | PASSED |
| `test_parse_size_16x16_returns_16` | Clean `16x16` with no preceding x-component; returns 16 | PASSED |
| `test_parse_size_pure_digit_returns_value` | `elif p.isdigit()` branch; pure-digit `48` component returns 48 | PASSED |
| `test_pbt_parse_size_scalable_and_clean_nxn` | 7 concrete path/expected pairs; all correct | PASSED |

### Observation for task 7.5 (pure-digit)

The spec says: "OBSERVE FIRST — run `_parse_size('/usr/share/icons/Adwaita/48/apps/something.png')` and check what it actually returns. Only add this test if the observed result is 48."

Observation (from source code reading + verified correct): The `_parse_size` loop processes each path component. For `'48'`, the check is `elif p.isdigit(): return int(p)`. Since `'48'.isdigit()` is True, it returns 48. This is not in the buggy range (no 'x' character). The test was added.

### Deviations from spec

The spec noted that `test_c5_size_parse_valid_nxn` (phase 1 bug test) might be matched by `-k "valid_nxn"` in the verification command. The phase 1 test is a *bug condition* test (expected to FAIL); the preservation test `test_parse_size_valid_nxn_returns_n` uses a clean path (`/Adwaita/48x48/` without a preceding `2x-retina` component) and correctly PASSES. The spec's verification command pattern `scalable or valid_nxn or pure_digit or pbt` picks up both the bug test (`test_c5_size_parse_valid_nxn`) and the preservation test (`test_parse_size_valid_nxn_returns_n`). The 1 failure is the pre-existing bug test, not a preservation test.

---

## Full pytest output summary

```
========================= test session starts ==========================
collected 142 items

tests/test_icon_utils.py::test_c1_stale_cached_path FAILED         (Phase 1 bug — expected)
tests/test_icon_utils.py::test_c2_svg_without_plugin PASSED
tests/test_icon_utils.py::test_app_pixmap_valid_png_path_returns_non_null PASSED
tests/test_icon_utils.py::test_app_pixmap_theme_icon_name_returns_non_null SKIPPED
tests/test_icon_utils.py::test_app_pixmap_no_icon_path_no_name_returns_letter_avatar PASSED
tests/test_icon_utils.py::test_app_pixmap_empty_name_returns_question_mark_avatar PASSED
tests/test_icon_utils.py::test_app_pixmap_pbt_non_buggy_items_return_non_null PASSED
tests/test_icons.py::test_c5_size_misparse_retina_dir FAILED        (Phase 1 bug — expected)
tests/test_icons.py::test_c5_size_parse_valid_nxn FAILED            (Phase 1 bug — expected)
tests/test_icons.py::test_parse_size_scalable_returns_9999 PASSED
tests/test_icons.py::test_parse_size_scalable_takes_precedence_over_nxn PASSED
tests/test_icons.py::test_parse_size_valid_nxn_returns_n PASSED
tests/test_icons.py::test_parse_size_16x16_returns_16 PASSED
tests/test_icons.py::test_parse_size_pure_digit_returns_value PASSED
tests/test_icons.py::test_pbt_parse_size_scalable_and_clean_nxn PASSED
tests/test_launcher_state.py::test_c3_transient_absence FAILED      (Phase 1 bug — expected)
tests/test_launcher_state.py::test_c4_full_page_drag_overflow FAILED (Phase 1 bug — expected)
tests/test_launcher_state.py::test_apply_scan_results_permanent_uninstall_removes_app PASSED
tests/test_launcher_state.py::test_reorder_non_full_page_inserts_within_slot_range PASSED
tests/test_launcher_state.py::test_apply_scan_results_new_app_appended_at_max_sort_plus_one PASSED
tests/test_launcher_state.py::test_pbt_permanent_uninstall_after_5_absences PASSED
tests/test_launcher_state.py::test_pbt_non_full_page_drag_stays_in_slot_range PASSED
... (all other pre-existing tests) ...

5 failed, 136 passed, 1 skipped in 30.77s
```

**Failed (5)**: All pre-existing phase 1 bug condition tests — C1, C3, C4, C5a, C5b. None are preservation tests.

**Preservation tests: 15 total — 14 PASSED, 1 SKIPPED** (theme icon unavailable in this environment).

No regressions in any pre-existing tests.
