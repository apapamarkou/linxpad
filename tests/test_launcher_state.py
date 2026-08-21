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
    state = make_state(apps={"x1": _app("x1", 0)})
    assert state.apply_scan_results([])
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

