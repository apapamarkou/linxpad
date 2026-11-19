# Phase 3 Report — Implementation (Tasks 8–12)

## Summary

All five bugs resolved. 143 tests pass, 1 skipped (theme icon unavailable in headless environment — expected). One pre-existing test (`test_apply_scan_removes_missing_apps`) was updated to reflect the new grace-period contract (approved by user during implementation).

---

## Task 8 — Null-pixmap guards in `app_pixmap()` and `load_app_icon()` (Bugs 1.1 & 1.2)

**File**: `src/linxpad/ui/components/icon_utils.py`

### Changes

`load_app_icon()` (lines 44–46 after fix):
- Replaced the full duplicated fallback chain with a single delegation:
  `label.setPixmap(app_pixmap(item, size, icon_resolver))`

`app_pixmap()` (lines 49–64 after fix):
- **`icon_path` branch** (line 55): added `pix.isNull()` check after `make_pixmap(icon_path, size)`. If null, falls through to the next branch instead of returning the null pixmap. Fixes Bug 1.2 (SVG without Qt plugin).
- **resolver branch** (lines 60–63): added `os.path.exists(resolved)` before calling `make_pixmap`. Also added `pix.isNull()` check on the result. If either check fails, falls through to `_fallback()`. Fixes Bug 1.1 (stale cached path).
- `QIcon.fromTheme` branch and `_fallback()` terminal branch unchanged.

### Test results

| Test | Result |
|------|--------|
| `test_c1_stale_cached_path` | PASSED (was FAIL) |
| `test_c2_svg_without_plugin` | PASSED (unchanged) |
| `test_app_pixmap_valid_png_path_returns_non_null` | PASSED |
| `test_app_pixmap_theme_icon_name_returns_non_null` | SKIPPED (no theme icon in headless env) |
| `test_app_pixmap_no_icon_path_no_name_returns_letter_avatar` | PASSED |
| `test_app_pixmap_empty_name_returns_question_mark_avatar` | PASSED |
| `test_app_pixmap_pbt_non_buggy_items_return_non_null` | PASSED |

---

## Task 9 — Grace period for transient `.desktop` absence (Bug 1.3)

**File**: `src/linxpad/core/launcher_state.py`

### Changes

`__init__()` (lines 29–43):
- Added `absence_grace: int = 3` parameter (default 3, existing callers unaffected).
- Added `self._absence_grace = absence_grace` field.
- Added `self._absence_counts: dict[str, int] = {}` field (transient, not persisted).

`apply_scan_results()` (lines 60–70):
- In the absence loop: replaced immediate `del self.apps[app_id]` with an increment of `self._absence_counts[app_id]`. Removal only occurs when count `>= self._absence_grace`. On removal, `pop()` clears the count.
- Added `self._absence_counts.pop(app_id, None)` in the present-key branch to reset the counter on reappearance.
- `changed` remains `False` within the grace window, suppressing unnecessary `save()` calls.

### Deviation from spec

The pre-existing test `test_apply_scan_removes_missing_apps` asserted immediate removal on a single empty scan. After user confirmation, it was updated to loop 3 times and assert removal only after the third scan, with intermediate assertions that the app survives scans 1 and 2.

**File**: `tests/test_launcher_state.py` (updated `test_apply_scan_removes_missing_apps`)

### Test results

| Test | Result |
|------|--------|
| `test_c3_transient_absence` | PASSED (was FAIL) |
| `test_apply_scan_removes_missing_apps` | PASSED (updated) |
| `test_apply_scan_results_permanent_uninstall_removes_app` | PASSED |
| `test_apply_scan_results_new_app_appended_at_max_sort_plus_one` | PASSED |
| `test_pbt_permanent_uninstall_after_5_absences` | PASSED |

---

## Task 10 — Full-page drag capacity check (Bug 1.4)

**File**: `src/linxpad/core/launcher_state.py`

### Changes

`_reorder_main()` (line ~196):
- Changed `if len(page_ids) > self._page_size:` to `if len(page_ids) >= self._page_size:`.
- One-character fix: `>` → `>=`. When the target page has exactly `page_size` items, the condition is now `True` and the move is blocked.

### Test results

| Test | Result |
|------|--------|
| `test_c4_full_page_drag_overflow` | PASSED (was FAIL) |
| `test_reorder_non_full_page_inserts_within_slot_range` | PASSED |
| `test_pbt_non_full_page_drag_stays_in_slot_range` | PASSED |
| `test_reorder_within_page` | PASSED |

---

## Task 11 — NxN size parser (Bug 1.5)

**File**: `src/linxpad/services/icons.py`

### Changes

`_parse_size()` (lines 50–59):
- Replaced the loose `"x" in p` check (which matched `2x-retina` and returned 2) with strict NxN validation:
  - `halves = p.split("x")`
  - Requires `len(halves) == 2`, both halves purely digits, and `int(halves[0]) == int(halves[1])` (must be square).
  - On match: `return int(halves[0])`. Otherwise: `continue` to next component.
- `elif p.isdigit()` branch for pure-numeric components unchanged.
- `"scalable" in parts` check unchanged (still first, still returns 9999).

For `"2x-retina"`: `split("x")` → `["2", "-retina"]`; `"-retina".isdigit()` is False → skipped.
For `"48x48"`: both `"48".isdigit()` True, `48 == 48` → returns 48.
For `"1024x768"`: both digits but `1024 != 768` → skipped.

### Test results

| Test | Result |
|------|--------|
| `test_c5_size_misparse_retina_dir` | PASSED (was FAIL) |
| `test_c5_size_parse_valid_nxn` | PASSED (was FAIL) |
| `test_parse_size_scalable_returns_9999` | PASSED |
| `test_parse_size_scalable_takes_precedence_over_nxn` | PASSED |
| `test_parse_size_valid_nxn_returns_n` | PASSED |
| `test_parse_size_16x16_returns_16` | PASSED |
| `test_parse_size_pure_digit_returns_value` | PASSED |
| `test_pbt_parse_size_scalable_and_clean_nxn` | PASSED |

---

## Task 12 — Cache re-validation in `IconResolver.resolve()`

**File**: `src/linxpad/services/icons.py`

### Changes

`resolve()` (lines 22–31):
- Cache-hit branch now checks `if cached is None or os.path.exists(cached): return cached`.
- If the cached path no longer exists on disk, falls through to `self._find(icon_name)` and updates `self._cache[icon_name]`.

**File**: `tests/test_icons.py` (two new tests added at end of file)

### New tests added

| Test | Verifies |
|------|---------|
| `test_resolve_stale_cached_path_evicts_and_resolves` | Stale cached path is evicted; `_find()` called; new path returned and cached |
| `test_resolve_valid_cached_path_returns_cached` | Valid cached path returned without calling `_find()` |

### Test results

| Test | Result |
|------|--------|
| `test_resolve_stale_cached_path_evicts_and_resolves` | PASSED |
| `test_resolve_valid_cached_path_returns_cached` | PASSED |

---

## Full final test suite output

```
============================= test session starts ==============================
platform linux -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /usr/bin/python3
cachedir: .pytest_cache
PyQt6 6.12.0 -- Qt runtime 6.12.0 -- Qt compiled 6.12.0
hypothesis profile 'default'
rootdir: /home/user/Projects/linxpad
configfile: pyproject.toml
plugins: qt-4.5.0, hypothesis-6.170.14, asyncio-1.5.0, cov-7.1.0, platformdirs-4.14.3
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None
collecting ... collected 144 items

tests/test_config.py::test_save_and_load_roundtrip PASSED
tests/test_config.py::test_load_missing_file_returns_empty PASSED
tests/test_config.py::test_is_empty PASSED
tests/test_config.py::test_load_corrupt_file PASSED
tests/test_desktop.py::test_parses_valid_desktop_file PASSED
tests/test_desktop.py::test_skips_nodisplay PASSED
tests/test_desktop.py::test_skips_non_application_type PASSED
tests/test_desktop.py::test_deduplicates_across_dirs PASSED
tests/test_desktop_watcher.py::TestHandler::test_desktop_file_created_triggers_callback PASSED
tests/test_desktop_watcher.py::TestHandler::test_non_desktop_file_ignored PASSED
tests/test_desktop_watcher.py::TestHandler::test_directory_event_ignored PASSED
tests/test_desktop_watcher.py::TestHandler::test_rapid_events_debounced_to_single_call PASSED
tests/test_desktop_watcher.py::TestHandler::test_deleted_triggers_callback PASSED
tests/test_desktop_watcher.py::TestHandler::test_modified_triggers_callback PASSED
tests/test_desktop_watcher.py::TestHandler::test_moved_to_desktop_triggers_callback PASSED
tests/test_desktop_watcher.py::TestHandler::test_moved_non_desktop_ignored PASSED
tests/test_desktop_watcher.py::TestDesktopWatcher::test_start_schedules_existing_dirs PASSED
tests/test_desktop_watcher.py::TestDesktopWatcher::test_start_skips_missing_dirs PASSED
tests/test_desktop_watcher.py::TestDesktopWatcher::test_stop_joins_observer PASSED
tests/test_desktop_watcher.py::TestDesktopWatcher::test_stop_before_start_is_safe PASSED
tests/test_drag_handler.py::TestDragSessionDataclass::test_default_compact_items_empty PASSED
tests/test_drag_handler.py::TestDragSessionDataclass::test_default_last_insert_idx_none PASSED
tests/test_drag_handler.py::TestDragSessionDataclass::test_default_foreign_ghost_none PASSED
tests/test_drag_handler.py::TestDragHandlerLifecycle::test_not_active_before_start PASSED
tests/test_drag_handler.py::TestDragHandlerLifecycle::test_active_after_start PASSED
tests/test_drag_handler.py::TestDragHandlerLifecycle::test_src_id_after_start PASSED
tests/test_drag_handler.py::TestDragHandlerLifecycle::test_src_icon_state_is_dragging PASSED
tests/test_drag_handler.py::TestDragHandlerLifecycle::test_compact_items_excludes_src PASSED
tests/test_drag_handler.py::TestDragHandlerLifecycle::test_not_active_after_cancel PASSED
tests/test_drag_handler.py::TestDragHandlerLifecycle::test_src_id_none_after_cancel PASSED
tests/test_drag_handler.py::TestDragHandlerLifecycle::test_icons_restored_after_cancel PASSED
tests/test_drag_handler.py::TestDragHandlerInsertIndex::test_left_half_of_first_slot_inserts_before PASSED
tests/test_drag_handler.py::TestDragHandlerInsertIndex::test_right_half_of_first_slot_inserts_after PASSED
tests/test_drag_handler.py::TestDragHandlerInsertIndex::test_left_half_of_second_slot_inserts_before_second PASSED
tests/test_drag_handler.py::TestDragHandlerInsertIndex::test_right_half_of_last_slot_inserts_at_end PASSED
tests/test_drag_handler.py::TestDragHandlerInsertIndex::test_empty_compact_returns_zero PASSED
tests/test_drag_handler.py::TestDragHandlerInsertIndex::test_result_always_in_valid_range PASSED
tests/test_drag_handler.py::TestDragHandlerFinishDrop::test_reorder_emitted_on_gap_drop PASSED
tests/test_drag_handler.py::TestDragHandlerFinishDrop::test_button_drop_emitted_on_icon_hit PASSED
tests/test_drag_handler.py::TestDragHandlerFinishDrop::test_not_active_after_finish PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_load_pages_sets_page_count PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_load_empty_creates_one_page PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_initial_page_is_zero PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_current_scene_has_correct_items PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_scene_at_returns_correct_page PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_scene_at_out_of_range_returns_none PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_go_to_page_changes_current_page PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_go_to_page_out_of_range_ignored PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_append_empty_page_increases_count PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_remove_trailing_empty_page PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_remove_trailing_does_not_remove_non_empty PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_remove_trailing_does_not_remove_last_page PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_load_pages_resets_to_page_zero PASSED
tests/test_grid_view.py::TestGridViewPageManagement::test_load_pages_clamps_current_page PASSED
tests/test_grid_view.py::TestGridViewSignals::test_page_changed_emitted_on_show_silent PASSED
tests/test_grid_view.py::TestGridViewSignals::test_item_clicked_emitted PASSED
tests/test_grid_view.py::TestGridViewSignals::test_background_clicked_emitted_on_empty_area PASSED
tests/test_grid_view.py::TestGridViewWheelNavigation::test_wheel_down_goes_to_next_page PASSED
tests/test_grid_view.py::TestGridViewWheelNavigation::test_wheel_up_goes_to_prev_page PASSED
tests/test_grid_view.py::TestGridViewWheelNavigation::test_next_page_at_last_does_nothing PASSED
tests/test_grid_view.py::TestGridViewWheelNavigation::test_prev_page_at_first_does_nothing PASSED
tests/test_grid_view.py::TestGridViewDragDrop::test_drag_enter_accepted_for_item_mime PASSED
tests/test_grid_view.py::TestGridViewDragDrop::test_drag_enter_ignored_for_non_item_mime PASSED
tests/test_grid_view.py::TestGridViewDragDrop::test_drop_event_ignored_when_no_active_drag PASSED
tests/test_grid_view.py::TestGridViewDragDrop::test_reorder_signal_emitted_after_drop PASSED
tests/test_icon_item.py::TestIconItemInitialState::test_app_initial_state_is_normal PASSED
tests/test_icon_item.py::TestIconItemInitialState::test_folder_initial_state_is_folder PASSED
tests/test_icon_item.py::TestIconItemInitialState::test_item_id PASSED
tests/test_icon_item.py::TestIconItemInitialState::test_bounding_rect_matches_cell PASSED
tests/test_icon_item.py::TestIconItemInitialState::test_size_matches_cell PASSED
tests/test_icon_item.py::TestIconItemStateTransitions::test_set_state_selected PASSED
tests/test_icon_item.py::TestIconItemStateTransitions::test_set_state_drop_target PASSED
tests/test_icon_item.py::TestIconItemStateTransitions::test_set_state_ghost PASSED
tests/test_icon_item.py::TestIconItemStateTransitions::test_set_state_dragging PASSED
tests/test_icon_item.py::TestIconItemStateTransitions::test_set_state_back_to_normal PASSED
tests/test_icon_item.py::TestIconItemStateTransitions::test_all_state_constants_are_distinct PASSED
tests/test_icon_item.py::TestIconItemSetItem::test_set_item_updates_id PASSED
tests/test_icon_item.py::TestIconItemSetItem::test_set_item_folder_updates_state PASSED
tests/test_icon_item.py::TestIconItemSetItem::test_set_item_app_resets_state_to_normal PASSED
tests/test_icon_item.py::TestIconItemCellResize::test_set_cell_size_updates_bounding_rect PASSED
tests/test_icon_item.py::TestIconItemCellResize::test_set_cell_size_updates_size PASSED
tests/test_icon_item.py::TestIconItemClickSignal::test_click_emits_item_id PASSED
tests/test_icon_utils.py::test_c1_stale_cached_path PASSED
tests/test_icon_utils.py::test_c2_svg_without_plugin PASSED
tests/test_icon_utils.py::test_app_pixmap_valid_png_path_returns_non_null PASSED
tests/test_icon_utils.py::test_app_pixmap_theme_icon_name_returns_non_null SKIPPED
tests/test_icon_utils.py::test_app_pixmap_no_icon_path_no_name_returns_letter_avatar PASSED
tests/test_icon_utils.py::test_app_pixmap_empty_name_returns_question_mark_avatar PASSED
tests/test_icon_utils.py::test_app_pixmap_pbt_non_buggy_items_return_non_null PASSED
tests/test_icons.py::test_c5_size_misparse_retina_dir PASSED
tests/test_icons.py::test_c5_size_parse_valid_nxn PASSED
tests/test_icons.py::test_parse_size_scalable_returns_9999 PASSED
tests/test_icons.py::test_parse_size_scalable_takes_precedence_over_nxn PASSED
tests/test_icons.py::test_parse_size_valid_nxn_returns_n PASSED
tests/test_icons.py::test_parse_size_16x16_returns_16 PASSED
tests/test_icons.py::test_parse_size_pure_digit_returns_value PASSED
tests/test_icons.py::test_pbt_parse_size_scalable_and_clean_nxn PASSED
tests/test_icons.py::test_resolve_stale_cached_path_evicts_and_resolves PASSED
tests/test_icons.py::test_resolve_valid_cached_path_returns_cached PASSED
tests/test_launcher_state.py::test_apply_scan_adds_new_apps PASSED
tests/test_launcher_state.py::test_apply_scan_removes_missing_apps PASSED
tests/test_launcher_state.py::test_create_folder_compacts_page_locally PASSED
tests/test_launcher_state.py::test_add_to_folder_compacts_page_locally PASSED
tests/test_launcher_state.py::test_remove_from_folder_dissolves_onto_same_page PASSED
tests/test_launcher_state.py::test_reorder_within_page PASSED
tests/test_launcher_state.py::test_get_main_items_by_page_groups_correctly PASSED
tests/test_launcher_state.py::test_repair_removes_stale_app_ids_from_folder PASSED
tests/test_launcher_state.py::test_repair_deletes_folder_with_only_stale_ids PASSED
tests/test_launcher_state.py::test_remove_from_folder_dissolves_when_remaining_id_is_stale PASSED
tests/test_launcher_state.py::test_remove_from_folder_dissolves_with_stale_remaining_id_unrepaired PASSED
tests/test_launcher_state.py::test_c3_transient_absence PASSED
tests/test_launcher_state.py::test_c4_full_page_drag_overflow PASSED
tests/test_launcher_state.py::test_apply_scan_results_permanent_uninstall_removes_app PASSED
tests/test_launcher_state.py::test_reorder_non_full_page_inserts_within_slot_range PASSED
tests/test_launcher_state.py::test_apply_scan_results_new_app_appended_at_max_sort_plus_one PASSED
tests/test_launcher_state.py::test_pbt_permanent_uninstall_after_5_absences PASSED
tests/test_launcher_state.py::test_pbt_non_full_page_drag_stays_in_slot_range PASSED
tests/test_page_scene.py::TestPageScenePopulation::test_count_matches_items PASSED
tests/test_page_scene.py::TestPageScenePopulation::test_empty_scene_has_zero_count PASSED
tests/test_page_scene.py::TestPageScenePopulation::test_icon_items_length PASSED
tests/test_page_scene.py::TestPageScenePopulation::test_icon_items_returns_copy PASSED
tests/test_page_scene.py::TestPageScenePositioning::test_first_item_at_origin PASSED
tests/test_page_scene.py::TestPageScenePositioning::test_second_item_offset_by_stride PASSED
tests/test_page_scene.py::TestPageScenePositioning::test_fourth_item_starts_second_row PASSED
tests/test_page_scene.py::TestPageScenePositioning::test_grid_pos_matches_item_pos PASSED
tests/test_page_scene.py::TestPageScenePositioning::test_scene_rect_covers_grid PASSED
tests/test_page_scene.py::TestPageSceneHitTesting::test_item_at_pos_returns_correct_item PASSED
tests/test_page_scene.py::TestPageSceneHitTesting::test_item_at_pos_second_column PASSED
tests/test_page_scene.py::TestPageSceneHitTesting::test_item_at_pos_second_row PASSED
tests/test_page_scene.py::TestPageSceneHitTesting::test_item_at_pos_returns_none_in_spacing_gap PASSED
tests/test_page_scene.py::TestPageSceneHitTesting::test_item_at_pos_ghost_not_returned PASSED
tests/test_page_scene.py::TestPageSceneLookup::test_item_by_id_found PASSED
tests/test_page_scene.py::TestPageSceneLookup::test_item_by_id_not_found PASSED
tests/test_page_scene.py::TestPageSceneSetCellSize::test_set_cell_size_repositions_items PASSED
tests/test_page_scene.py::TestPageSceneSetCellSize::test_set_cell_size_updates_scene_rect PASSED
tests/test_page_scene.py::TestPageSceneIndexAtPos::test_index_at_origin PASSED
tests/test_page_scene.py::TestPageSceneIndexAtPos::test_index_second_column PASSED
tests/test_page_scene.py::TestPageSceneIndexAtPos::test_index_clamped_to_bounds PASSED
tests/test_rescan.py::test_rescan_calls_load_scan_apply PASSED
tests/test_rescan.py::test_rescan_notifies_instance_when_changed PASSED
tests/test_rescan.py::test_rescan_does_not_notify_when_unchanged PASSED
tests/test_rescan.py::test_main_rescan_flag_does_not_start_qt PASSED
tests/test_rescan.py::test_main_no_rescan_flag_starts_qt PASSED
tests/test_rescan.py::test_watcher_triggers_rescan_on_main_thread PASSED

======================= 143 passed, 1 skipped in 30.28s ========================
```

---

## Deviations from spec

1. **`test_apply_scan_removes_missing_apps` updated** — the pre-existing test asserted immediate removal after one empty scan. The grace period fix changes this contract. After user confirmation (option 1), the test was updated to loop 3 times and assert: not changed + app present after scan 1; not changed + app present after scan 2; changed + app absent after scan 3. This is the only change to test files beyond the two Task 12 additions.
