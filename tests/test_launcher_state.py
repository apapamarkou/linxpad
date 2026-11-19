# Failure output on unfixed code:
# FAILED tests/test_launcher_state.py::test_c3_transient_absence
#   AssertionError: App should survive first empty scan (transient absence).
#   Bug 1.3: app deleted immediately on first empty scan. 'abc-123' in {} is False.
# FAILED tests/test_launcher_state.py::test_c4_full_page_drag_overflow
#   AssertionError: Dragged item x50 sort_id should remain 48 (page 0 is full), got 5.
#   Bug 1.4: reorder allowed overflow onto full page (len(page_ids) > page_size misses == case).

from hypothesis import given, settings
from hypothesis import strategies as st

from linxpad.core.launcher_state import PAGE_SIZE, LauncherState
from linxpad.models import Application, Folder
from linxpad.services import DesktopScanner, IconResolver


class _FakeConfig:
    def __init__(self):
        self._apps = {}
        self._folders = {}

    def load(self):
        return self._apps, self._folders

    def save(self, apps, folders):
        self._apps = apps
        self._folders = folders

    def is_empty(self):
        return not self._apps and not self._folders


def make_state(apps=None, folders=None):
    cfg = _FakeConfig()
    cfg._apps = apps or {}
    cfg._folders = folders or {}
    state = LauncherState(cfg, DesktopScanner(IconResolver()), IconResolver())
    state.load()
    return state


def _app(id_, sort_id, folder_id=None):
    return Application(
        id=id_, name=id_, exec=f"{id_}.desktop", sort_id=sort_id, folder_id=folder_id
    )


def test_apply_scan_adds_new_apps():
    state = make_state()
    changed = state.apply_scan_results(
        [{"name": "Firefox", "exec": "firefox.desktop", "icon": None, "icon_name": "firefox"}]
    )
    assert changed
    assert any(a.name == "Firefox" for a in state.apps.values())


def test_apply_scan_removes_missing_apps():
    # Grace period is 3: app survives first two absences, removed on the third.
    state = make_state(apps={"x1": _app("x1", 0)})
    assert not state.apply_scan_results([])  # count=1, within grace — no change
    assert "x1" in state.apps
    assert not state.apply_scan_results([])  # count=2, within grace — no change
    assert "x1" in state.apps
    assert state.apply_scan_results([])  # count=3, grace exhausted — removed
    assert "x1" not in state.apps


def test_create_folder_compacts_page_locally():
    """app2 leaves page 0; items after it on page 0 shift left. Page 1 untouched."""
    # Page 0: a0(0), a1(1), a2(2), a3(3)
    # Page 1: b0(24)
    apps = {
        "a0": _app("a0", 0),
        "a1": _app("a1", 1),
        "a2": _app("a2", 2),
        "a3": _app("a3", 3),
        "b0": _app("b0", PAGE_SIZE),
    }
    state = make_state(apps=apps)
    fid = state.create_folder("a0", "a2")  # folder at slot 0, a2 leaves page 0

    pages = state.get_main_items_by_page()
    page0_ids = [i["id"] for i in pages[0]]
    # folder at 0, a1 at 1, a3 at 2 — a2's gap closed, empty slot at end of page 0
    assert page0_ids == [fid, "a1", "a3"]
    assert all(i["sortId"] // PAGE_SIZE == 0 for i in pages[0])
    # Page 1 untouched
    assert pages[1][0]["id"] == "b0"
    assert pages[1][0]["sortId"] == PAGE_SIZE


def test_add_to_folder_compacts_page_locally():
    """App added to folder leaves a gap on its page; later items shift left."""
    # Page 0: f1(0), a1(1), a2(2)
    # Page 1: b0(24)
    a1 = _app("a1", 1)
    a2 = _app("a2", 2)
    b0 = _app("b0", PAGE_SIZE)
    f1_app = _app("fa", 10, folder_id="f1")  # internal sort_id, not on main grid
    f1 = Folder(id="f1", name="F", app_ids=["fa"], sort_id=0)
    state = make_state(
        apps={"fa": f1_app, "a1": a1, "a2": a2, "b0": b0},
        folders={"f1": f1},
    )
    state.add_to_folder("f1", "a1")  # a1 leaves page 0

    pages = state.get_main_items_by_page()
    page0_ids = [i["id"] for i in pages[0]]
    assert page0_ids == ["f1", "a2"]
    assert pages[0][0]["sortId"] == 0
    assert pages[0][1]["sortId"] == 1
    # Page 1 untouched
    assert pages[1][0]["sortId"] == PAGE_SIZE


def test_remove_from_folder_dissolves_onto_same_page():
    """Dissolving a folder places both apps on the folder's page."""
    a1 = _app("a1", 0, folder_id="f1")
    a2 = _app("a2", 1, folder_id="f1")
    a3 = _app("a3", PAGE_SIZE)  # page 1
    f1 = Folder(id="f1", name="F", app_ids=["a1", "a2"], sort_id=5)
    state = make_state(apps={"a1": a1, "a2": a2, "a3": a3}, folders={"f1": f1})
    deleted = state.remove_from_folder("a1")
    assert deleted == "f1"
    pages = state.get_main_items_by_page()
    page0_ids = [i["id"] for i in pages[0]]
    assert "a1" in page0_ids
    assert "a2" in page0_ids
    # Both on page 0
    assert all(i["sortId"] // PAGE_SIZE == 0 for i in pages[0])
    # Page 1 untouched
    assert pages[1][0]["id"] == "a3"
    assert pages[1][0]["sortId"] == PAGE_SIZE


def test_reorder_within_page():
    a1 = _app("a1", 0)
    a2 = _app("a2", 1)
    a3 = _app("a3", 2)
    state = make_state(apps={"a1": a1, "a2": a2, "a3": a3})
    state.reorder("a3", "a1", "before", False, None)
    ids = [i["id"] for i in state.get_main_items()]
    assert ids == ["a3", "a1", "a2"]
    # All still on page 0
    assert all(state.apps[id_].sort_id // PAGE_SIZE == 0 for id_ in ["a1", "a2", "a3"])


def test_get_main_items_by_page_groups_correctly():
    apps = {str(i): _app(str(i), i) for i in range(PAGE_SIZE + 3)}
    state = make_state(apps=apps)
    pages = state.get_main_items_by_page()
    assert len(pages) == 2
    assert len(pages[0]) == PAGE_SIZE
    assert len(pages[1]) == 3


def test_repair_removes_stale_app_ids_from_folder():
    """Folder with a stale app ID (not in apps) has it stripped on load."""
    a1 = _app("a1", 0, folder_id="f1")
    f1 = Folder(id="f1", name="F", app_ids=["a1", "stale-id"], sort_id=5)
    state = make_state(apps={"a1": a1}, folders={"f1": f1})
    assert "stale-id" not in state.folders["f1"].app_ids
    assert "a1" in state.folders["f1"].app_ids


def test_repair_deletes_folder_with_only_stale_ids():
    """Folder whose every app ID is stale is deleted on load (FolderGhost case)."""
    f1 = Folder(id="f1", name="FolderGhost", app_ids=["stale-id"], sort_id=5)
    state = make_state(apps={}, folders={"f1": f1})
    assert "f1" not in state.folders


def test_remove_from_folder_dissolves_when_remaining_id_is_stale():
    """Folder dissolves even if the last remaining app ID is stale."""
    a1 = _app("a1", 0, folder_id="f1")
    # f1 has a1 (live) and stale-id (dead) — simulates the FolderGhost scenario
    f1 = Folder(id="f1", name="FolderGhost", app_ids=["a1", "stale-id"], sort_id=5)
    state = make_state(apps={"a1": a1}, folders={"f1": f1})
    # After load, stale-id is stripped — folder now has only a1
    assert state.folders["f1"].app_ids == ["a1"]
    # Dragging a1 out should dissolve the folder
    deleted = state.remove_from_folder("a1")
    assert deleted == "f1"
    assert "f1" not in state.folders
    assert state.apps["a1"].folder_id is None


def test_remove_from_folder_dissolves_with_stale_remaining_id_unrepaired():
    """Folder dissolves via remove_from_folder even without prior repair.

    Directly tests the fix in remove_from_folder: folder.app_ids.clear()
    runs regardless of whether the last remaining ID resolves to a live app.
    """
    a1 = _app("a1", 0, folder_id="f1")
    a2 = _app("a2", 1, folder_id="f1")
    f1 = Folder(id="f1", name="F", app_ids=["a1", "a2"], sort_id=5)
    state = make_state(apps={"a1": a1, "a2": a2}, folders={"f1": f1})
    # Simulate a2 becoming stale after load (e.g. removed by scanner)
    del state.apps["a2"]
    # Dragging a1 out — a2 is now a stale ID, folder must still dissolve
    deleted = state.remove_from_folder("a1")
    assert deleted == "f1"
    assert "f1" not in state.folders
    assert state.apps["a1"].folder_id is None


def test_c3_transient_absence():
    """Bug 1.3: apply_scan_results([]) deletes apps immediately.
    MUST FAIL on unfixed code: app is removed after a single empty scan.
    """
    state = make_state()
    app = Application(id="abc-123", sort_id=5, name="Firefox", exec="firefox.desktop")
    state.apps["abc-123"] = app

    state.apply_scan_results([])
    assert "abc-123" in state.apps, (
        "App should survive first empty scan (transient absence). "
        "Bug 1.3: app deleted immediately on first empty scan."
    )

    state.apply_scan_results([])
    assert "abc-123" in state.apps, (
        "App should survive second empty scan. " "Bug 1.3: app still not present after second scan."
    )


def test_c4_full_page_drag_overflow():
    """Bug 1.4: reorder allows dragging onto a full page because len(page_ids) > page_size
    misses the == case.
    MUST FAIL on unfixed code: dragged item ends up with sort_id on the full page.
    """
    state = make_state()
    # Create PAGE_SIZE apps on page 0, sort_ids 0..23
    apps_on_page0 = []
    for i in range(PAGE_SIZE):
        uid = f"app-p0-{i:02d}"
        app = Application(id=uid, sort_id=i, name=f"App{i}", exec=f"app{i}.desktop")
        state.apps[uid] = app
        apps_on_page0.append(uid)
    # One app on page 2, sort_id=48
    state.apps["x50"] = Application(id="x50", sort_id=48, name="X50", exec="x50.desktop")

    # Drag x50 onto page 0 (target = app at sort_id 5)
    state.reorder("x50", "app-p0-05", "before", False, None)

    dragged = state.apps["x50"]
    assert dragged.sort_id == 48, (
        f"Dragged item x50 sort_id should remain 48 (page 0 is full), got {dragged.sort_id}. "
        "Bug 1.4: reorder allowed overflow onto full page."
    )
    for uid in apps_on_page0:
        a = state.apps[uid]
        assert a.sort_id <= 23, (
            f"App {uid} sort_id {a.sort_id} overflowed page 0 boundary. " "Bug 1.4."
        )


# ── Phase 2: Preservation property tests (Task 6) ────────────────────────────
# These tests MUST PASS on unfixed code. They encode correct baseline behavior
# for inputs that do NOT trigger the bugs.


def test_apply_scan_results_permanent_uninstall_removes_app():
    """Preservation: after 5 consecutive empty scans, an app is absent from state.

    On unfixed code the app is removed on the very first empty scan, so after
    5 scans the app is certainly absent. On fixed code (with a grace period of
    N absences) the app is also absent after 5 consecutive absences as long as
    N <= 5. This assertion holds on both unfixed and fixed code.
    MUST PASS on unfixed code.
    """
    state = make_state()
    app = Application(id="perm-123", sort_id=0, name="OldApp", exec="old.desktop")
    state.apps["perm-123"] = app

    for _ in range(5):
        state.apply_scan_results([])

    assert "perm-123" not in state.apps, "App should be absent after 5 consecutive empty scans."


def test_reorder_non_full_page_inserts_within_slot_range():
    """Preservation: dragging to a page with fewer than page_size items keeps
    all sort_ids within that page's slot range [base, base + page_size - 1].

    Uses page 1 (base=24) with 3 items and drags an item from page 0 to it.
    On unfixed code this is a non-buggy path (len(page_ids)=3 < page_size=24,
    so the capacity guard does not apply). MUST PASS on unfixed code.
    """
    # Page 0: a0(0)
    # Page 1: b0(24), b1(25), b2(26)
    apps = {
        "a0": _app("a0", 0),
        "b0": _app("b0", PAGE_SIZE),
        "b1": _app("b1", PAGE_SIZE + 1),
        "b2": _app("b2", PAGE_SIZE + 2),
    }
    state = make_state(apps=apps)

    # Drag a0 (page 0) onto b1 (page 1) — page 1 has 3 items, well under 24
    state.reorder("a0", "b1", "before", False, None)

    base = PAGE_SIZE
    for app in state.apps.values():
        if app.folder_id is None and app.sort_id // PAGE_SIZE == 1:
            assert base <= app.sort_id <= base + PAGE_SIZE - 1, (
                f"App {app.id} sort_id {app.sort_id} outside page 1 slot range "
                f"[{base}, {base + PAGE_SIZE - 1}]."
            )


def test_apply_scan_results_new_app_appended_at_max_sort_plus_one():
    """Preservation: a newly discovered app gets sort_id = max_existing_sort_id + 1.

    apply_scan_results computes max_sort = max over all existing app and folder
    sort_ids, then assigns max_sort + 1 to each new app in sequence.
    MUST PASS on unfixed code.
    """
    state = make_state(
        apps={
            "a1": _app("a1", 5),
            "a2": _app("a2", 10),
        }
    )
    # found contains both existing apps plus one new one
    found = [
        {"name": "a1", "exec": "a1.desktop", "icon": None, "icon_name": None},
        {"name": "a2", "exec": "a2.desktop", "icon": None, "icon_name": None},
        {"name": "NewApp", "exec": "newapp.desktop", "icon": None, "icon_name": None},
    ]
    state.apply_scan_results(found)

    new_app = next((a for a in state.apps.values() if a.name == "NewApp"), None)
    assert new_app is not None, "NewApp should have been added by apply_scan_results"
    assert (
        new_app.sort_id == 11
    ), f"Expected new app sort_id 11 (max_existing=10, +1), got {new_app.sort_id}."


# Small concrete initial app configurations for property-based tests
_INITIAL_APP_CONFIGS = [
    {"id": "app-a", "sort_id": 0, "name": "Alpha", "exec": "alpha.desktop"},
    {"id": "app-b", "sort_id": 5, "name": "Beta", "exec": "beta.desktop"},
    {"id": "app-c", "sort_id": 10, "name": "Gamma", "exec": "gamma.desktop"},
]


@settings(max_examples=len(_INITIAL_APP_CONFIGS))
@given(st.sampled_from(_INITIAL_APP_CONFIGS))
def test_pbt_permanent_uninstall_after_5_absences(app_cfg):
    """Property: for any initial app, 5 consecutive empty scans remove the app.

    Unfixed code removes on the first scan; fixed code removes after N <= 5.
    Either way the app is absent after 5 consecutive absences.
    MUST PASS on unfixed code.
    """
    state = make_state()
    app = Application(
        id=app_cfg["id"],
        sort_id=app_cfg["sort_id"],
        name=app_cfg["name"],
        exec=app_cfg["exec"],
    )
    state.apps[app_cfg["id"]] = app

    for _ in range(5):
        state.apply_scan_results([])

    assert (
        app_cfg["id"] not in state.apps
    ), f"App {app_cfg['id']} should be absent after 5 consecutive empty scans."


@settings(max_examples=20)
@given(st.integers(min_value=1, max_value=20))
def test_pbt_non_full_page_drag_stays_in_slot_range(item_count):
    """Property: dragging to a page with fewer than page_size items keeps
    all resulting sort_ids within that page's slot range.

    For any target page with 1-20 items (all < PAGE_SIZE=24), a cross-page
    drag must succeed and all items on the target page must have sort_ids
    in [base, base + page_size - 1]. MUST PASS on unfixed code.
    """
    # Build page 1 (target) with item_count items and page 0 with 1 item to drag
    apps = {"drag-src": _app("drag-src", 0)}  # page 0, slot 0
    for i in range(item_count):
        uid = f"tgt-{i:02d}"
        apps[uid] = _app(uid, PAGE_SIZE + i)  # page 1, slots 24..23+item_count
    state = make_state(apps=apps)

    # Drag the page-0 item onto the first item of page 1
    target_id = "tgt-00"
    state.reorder("drag-src", target_id, "before", False, None)

    base = PAGE_SIZE
    for app in state.apps.values():
        if app.folder_id is None and app.sort_id // PAGE_SIZE == 1:
            assert base <= app.sort_id <= base + PAGE_SIZE - 1, (
                f"App {app.id} sort_id {app.sort_id} outside page 1 slot range "
                f"[{base}, {base + PAGE_SIZE - 1}] after dragging into {item_count}-item page."
            )
