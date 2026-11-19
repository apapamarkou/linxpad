# Source Files for Icon Fix Phase 1

## /home/user/Projects/linxpad/src/linxpad/ui/components/icon_utils.py

```python
#  _     _                            _
# | |   (_)_ __ __  ___ __   __ _  __| |
# | |   | | '_ \\ \/ / '_ \ / _` |/ _` |
# | |___| | | | |>  <| |_) | (_| | (_| |
# |_____|_|_| |_/_/\_\ .__/ \__,_|\__,_|
#                    |_|
#
# Author: Andrianos Papamarkou
# Licence: GPL3
# https://github.com/apapamarkou/linxpad
# https://apapamarkou.github.io/linxpad/

"""Icon loading utilities — no Qt widgets, only QPixmap / QIcon."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap


def make_pixmap(path: str, size: int) -> QPixmap:
    return QPixmap(path).scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _fallback(size: int, letter: str) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(QColor("#2d2d2d"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor("#ffffff"))
    f = QFont()
    f.setBold(True)
    f.setPointSize(max(8, int(size * 0.4)))
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    p.end()
    return pix


def load_app_icon(label, item: dict, size: int, icon_resolver=None) -> None:
    """Load an app icon into a QLabel with fallback chain."""
    icon_path = item.get("icon")
    icon_name = item.get("icon_name")

    if icon_path and os.path.exists(icon_path):
        label.setPixmap(make_pixmap(icon_path, size))
        return
    if icon_name:
        qi = QIcon.fromTheme(icon_name)
        if not qi.isNull():
            label.setPixmap(qi.pixmap(size, size))
            return
    if icon_name and icon_resolver:
        resolved = icon_resolver.resolve(icon_name)
        if resolved:
            label.setPixmap(make_pixmap(resolved, size))
            return

    label.setPixmap(_fallback(size, (item.get("name") or "?")[0].upper()))


def app_pixmap(item: dict, size: int, icon_resolver=None) -> QPixmap:
    """Return a QPixmap for an app item (no QLabel needed)."""
    icon_path = item.get("icon")
    icon_name = item.get("icon_name")

    if icon_path and os.path.exists(icon_path):
        return make_pixmap(icon_path, size)
    if icon_name:
        qi = QIcon.fromTheme(icon_name)
        if not qi.isNull():
            return qi.pixmap(size, size)
    if icon_name and icon_resolver:
        resolved = icon_resolver.resolve(icon_name)
        if resolved:
            return make_pixmap(resolved, size)

    return _fallback(size, (item.get("name") or "?")[0].upper())


def load_folder_icon(label, size: int) -> None:
    """Load a folder icon into a QLabel."""
    pix = folder_pixmap(size)
    label.setPixmap(pix)


def folder_collage_pixmap(children: list[dict], size: int, icon_resolver=None) -> QPixmap:
    """2×2 collage of up to 4 child app icons on a rounded folder background."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Rounded background
    from PyQt6.QtGui import QPainterPath

    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, size * 0.18, size * 0.18)
    p.fillPath(path, QColor(80, 80, 80, 200))

    n = min(len(children), 4)
    pad = int(size * 0.12)
    gap = int(size * 0.04)
    child_size = (size - 2 * pad - gap) // 2

    for i, child in enumerate(children[:n]):
        col, row = i % 2, i // 2
        x = pad + col * (child_size + gap)
        y = pad + row * (child_size + gap)
        child_px = app_pixmap(child, child_size, icon_resolver)
        p.drawPixmap(
            x,
            y,
            child_px.scaled(
                child_size,
                child_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ),
        )

    p.end()
    return pix


def folder_pixmap(size: int) -> QPixmap:
    """Return a QPixmap for a folder."""
    qi = QIcon.fromTheme("folder")
    if not qi.isNull():
        return qi.pixmap(size, size)
    return _fallback(size, "📁")
```

---

## /home/user/Projects/linxpad/src/linxpad/core/launcher_state.py

```python
#  _     _                            _
# | |   (_)_ __ __  ___ __   __ _  __| |
# | |   | | '_ \\ \/ / '_ \ / _` |/ _` |
# | |___| | | | |>  <| |_) | (_| | (_| |
# |_____|_|_| |_/_/\_\ .__/ \__,_|\__,_|
#                    |_|
#
# Author: Andrianos Papamarkou
# Licence: GPL3
# https://github.com/apapamarkou/linxpad
# https://apapamarkou.github.io/linxpad/

import logging
import uuid

from ..models import Application, Folder
from ..services import ConfigService, DesktopScanner, IconResolver

logger = logging.getLogger(__name__)

PAGE_SIZE = 24  # default: 8 columns × 3 rows


class LauncherState:
    """Holds all mutable launcher data and business logic. No Qt dependency."""

    def __init__(
        self,
        config: ConfigService,
        scanner: DesktopScanner,
        icons: IconResolver,
        page_size: int = PAGE_SIZE,
    ):
        self._config = config
        self._scanner = scanner
        self._icons = icons
        self._page_size = page_size
        self.apps: dict[str, Application] = {}
        self.folders: dict[str, Folder] = {}

    @property
    def icons(self) -> IconResolver:
        return self._icons

    # ── persistence ──────────────────────────────────────────────────────────

    def load(self) -> None:
        self.apps, self.folders = self._config.load()
        self._repair_folder_ids()
        self._ensure_sort_ids()

    def save(self) -> None:
        self._config.save(self.apps, self.folders)

    def is_first_run(self) -> bool:
        return self._config.is_empty()

    # ── discovery ────────────────────────────────────────────────────────────

    def apply_scan_results(self, found: list[dict]) -> bool:
        """Merge scan results into current state. Returns True if changed."""
        found_keys = {(a["name"], a["exec"]) for a in found}
        managed_keys = {(a.name, a.exec): k for k, a in self.apps.items()}
        changed = False

        for key, app_id in list(managed_keys.items()):
            if key not in found_keys:
                # Compact the page this app was on before removing it
                self._compact_page_of(self.apps[app_id].sort_id)
                del self.apps[app_id]
                changed = True

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

    # ── grid helpers ─────────────────────────────────────────────────────────

    def get_main_items(self) -> list[dict]:
        """Flat list of all main-view items sorted by sort_id."""
        items = [{**a.to_dict(), "type": "app"} for a in self.apps.values() if a.folder_id is None]
        items += [self._folder_dict(f) for f in self.folders.values()]
        return sorted(items, key=lambda x: x["sortId"])

    def get_main_items_by_page(self) -> list[list[dict]]:
        """Items grouped by page derived from sort_id.

        Rules enforced here (no data mutation):
        - New apps appended after max sort_id land on a new page when the
          last page is full (sort_id // self._page_size is already correct).
        - Trailing empty pages are stripped so the view never shows a blank
          last page after removals or folder operations.
        """
        flat = self.get_main_items()
        if not flat:
            return [[]]
        max_page = flat[-1]["sortId"] // self._page_size
        pages: list[list[dict]] = [[] for _ in range(max_page + 1)]
        for item in flat:
            pages[item["sortId"] // self._page_size].append(item)
        # Drop trailing empty pages
        while len(pages) > 1 and not pages[-1]:
            pages.pop()
        return pages

    def get_folder_items(self, folder_id: str) -> list[dict]:
        folder = self.folders.get(folder_id)
        if not folder:
            return []
        result = [
            {**self.apps[aid].to_dict(), "type": "app"}
            for aid in folder.app_ids
            if aid in self.apps
        ]
        return sorted(result, key=lambda x: x["sortId"])

    # ── folder operations ────────────────────────────────────────────────────

    def create_folder(self, app1_id: str, app2_id: str) -> str:
        """Replace app1 with a folder at app1's position.

        app2 moves inside the folder — its slot on its page is compacted
        (items after it on that page shift left, leaving an empty slot at
        the end of that page).
        """
        app1 = self.apps[app1_id]
        app2 = self.apps[app2_id]
        folder_id = str(uuid.uuid4())
        self.folders[folder_id] = Folder(
            id=folder_id,
            name="App Folder",
            app_ids=[app1_id, app2_id],
            sort_id=app1.sort_id,
        )
        app2_sort = app2.sort_id
        app1.folder_id = folder_id
        app1.sort_id = 0
        app2.folder_id = folder_id
        app2.sort_id = 1
        # Compact the page app2 left (app1's slot is now taken by the folder)
        self._compact_page_of(app2_sort)
        self.save()
        return folder_id

    def add_to_folder(self, folder_id: str, app_id: str) -> None:
        folder = self.folders.get(folder_id)
        app = self.apps.get(app_id)
        if not folder or not app or app_id in folder.app_ids:
            return
        next_sort = (
            max((self.apps[aid].sort_id for aid in folder.app_ids if aid in self.apps), default=-1)
            + 1
        )
        app_sort = app.sort_id
        folder.app_ids.append(app_id)
        app.folder_id = folder_id
        app.sort_id = next_sort
        # Compact the page the app left
        self._compact_page_of(app_sort)
        self.save()

    def remove_from_folder(self, app_id: str) -> str | None:
        """Remove app from its folder. Returns folder_id if folder was deleted."""
        app = self.apps.get(app_id)
        if not app:
            return None

        if not app.folder_id:
            for fid, folder in self.folders.items():
                if app_id in folder.app_ids:
                    app.folder_id = fid
                    break

        if not app.folder_id:
            return None

        folder_id = app.folder_id
        folder = self.folders.get(folder_id)
        folder_sort = folder.sort_id if folder else 0
        folder_page = folder_sort // self._page_size

        # Count items currently on the folder's page
        page_count = sum(
            1
            for a in self.apps.values()
            if a.folder_id is None and a.sort_id // self._page_size == folder_page
        ) + sum(1 for f in self.folders.values() if f.sort_id // self._page_size == folder_page)
        will_delete_folder = folder is not None and len(folder.app_ids) <= 2
        # If folder dissolves, its slot is reused — net change is +1 (the last remaining app).
        # If folder stays, the ejected app needs a free slot on the page.
        slots_needed = 1 if will_delete_folder else 1
        if page_count + slots_needed > self._page_size:
            return None  # page full — action blocked

        if folder and app_id in folder.app_ids:
            folder.app_ids.remove(app_id)

        will_delete_folder = folder is not None and len(folder.app_ids) <= 1

        if will_delete_folder:
            # Folder dissolves: ejected app takes the folder's slot;
            # last remaining app goes to the next slot on the same page
            # (or the first slot of the next page if the page is full).
            app.folder_id = None
            app.sort_id = folder_sort
            if folder and folder.app_ids:
                last_app = self.apps.get(folder.app_ids[0])
                if last_app:
                    last_app.folder_id = None
                    last_app.sort_id = self._next_slot_on_page(folder_page, exclude=folder_sort)
                folder.app_ids.clear()
        else:
            # Folder stays: append ejected app at the end of the folder's page
            app.folder_id = None
            app.sort_id = self._next_slot_on_page(folder_page)

        deleted_folder = None
        if folder and not folder.app_ids:
            del self.folders[folder_id]
            deleted_folder = folder_id

        self.save()
        return deleted_folder

    def rename_folder(self, folder_id: str, name: str) -> None:
        if folder_id in self.folders:
            self.folders[folder_id].name = name
            self.save()

    # ── reorder ──────────────────────────────────────────────────────────────

    def move_to_page(self, item_id: str, page: int) -> None:
        """Move item to slot 0 of the given page, compacting the page it left."""
        obj = self.apps.get(item_id) or self.folders.get(item_id)
        if not obj:
            return
        old_sort = obj.sort_id
        obj.sort_id = page * self._page_size
        self._compact_page_of(old_sort)
        self.save()

    def move_to_first_empty_slot(self, item_id: str, page: int) -> bool:
        """Move item to the first empty slot on the given page.

        Returns True on success, False if the target page is full.
        """
        obj = self.apps.get(item_id) or self.folders.get(item_id)
        if not obj:
            return False
        occupied = {a.sort_id for a in self.apps.values() if a.folder_id is None} | {
            f.sort_id for f in self.folders.values()
        }
        occupied.discard(obj.sort_id)  # exclude the item itself
        base = page * self._page_size
        slot = next((s for s in range(self._page_size) if base + s not in occupied), None)
        if slot is None:
            return False  # page full
        old_sort = obj.sort_id
        obj.sort_id = base + slot
        self._compact_page_of(old_sort)
        self.save()
        return True

    def reorder(
        self,
        dragged_id: str,
        target_id: str,
        placement: str,
        in_folder: bool,
        folder_id: str | None,
    ) -> None:
        if dragged_id == target_id:
            return
        if in_folder and folder_id:
            self._reorder_in_folder(dragged_id, target_id, placement, folder_id)
        else:
            self._reorder_main(dragged_id, target_id, placement)
        self.save()

    def _reorder_main(self, dragged_id: str, target_id: str, placement: str) -> None:
        """Reorder within a single page; cross-page drags move to target's page."""
        items = self.get_main_items()
        ids = [i["id"] for i in items]
        if dragged_id not in ids or target_id not in ids:
            return

        target_obj = self.apps.get(target_id) or self.folders.get(target_id)
        if not target_obj:
            return
        target_page = target_obj.sort_id // self._page_size

        # Collect ids on the target page in order
        page_ids = [i["id"] for i in items if i["sortId"] // self._page_size == target_page]

        # Remove dragged from page list (it may be on a different page)
        dragged_obj = self.apps.get(dragged_id) or self.folders.get(dragged_id)
        if not dragged_obj:
            return

        if dragged_id in page_ids:
            page_ids.remove(dragged_id)
        else:
            # Dragged from a different page: block if target page is already full
            if len(page_ids) > self._page_size:
                return
            self._compact_page_of(dragged_obj.sort_id)

        ti = page_ids.index(target_id)
        page_ids.insert(ti + (1 if placement == "after" else 0), dragged_id)

        # Reassign sort_ids within the target page
        base = target_page * self._page_size
        for slot, item_id in enumerate(page_ids):
            obj = self.apps.get(item_id) or self.folders.get(item_id)
            if obj:
                obj.sort_id = base + slot

    def _reorder_in_folder(
        self, dragged_id: str, target_id: str, placement: str, folder_id: str
    ) -> None:
        items = self.get_folder_items(folder_id)
        ids = [i["id"] for i in items]
        if dragged_id not in ids or target_id not in ids:
            return
        ids.remove(dragged_id)
        ti = ids.index(target_id)
        ids.insert(ti + (1 if placement == "after" else 0), dragged_id)
        for sort_id, item_id in enumerate(ids):
            app = self.apps.get(item_id)
            if app:
                app.sort_id = sort_id

    # ── private ──────────────────────────────────────────────────────────────

    def _page_items(self, page: int) -> list:
        """All main-view objects (Application or Folder) on the given page, sorted."""
        result = []
        for a in self.apps.values():
            if a.folder_id is None and a.sort_id // self._page_size == page:
                result.append(a)
        for f in self.folders.values():
            if f.sort_id // self._page_size == page:
                result.append(f)
        return sorted(result, key=lambda x: x.sort_id)

    def _compact_page_of(self, sort_id: int) -> None:
        """After removing an item at sort_id, shift later items on that page left.

        Items on other pages are untouched. The empty slot appears at the
        end of the page.
        """
        page = sort_id // self._page_size
        base = page * self._page_size
        items = self._page_items(page)
        # Remove the item that no longer belongs to the main view
        # (it has already been moved to a folder or deleted by the caller)
        items = [
            obj
            for obj in items
            if obj.sort_id != sort_id
            or (hasattr(obj, "folder_id") and obj.folder_id is None)
            or not hasattr(obj, "folder_id")
        ]
        for slot, obj in enumerate(items):
            obj.sort_id = base + slot

    def _next_slot_on_page(self, page: int, exclude: int | None = None) -> int:
        """Return the first free sort_id on the given page.

        If the page is full, spills to the next page.
        """
        occupied = set()
        for a in self.apps.values():
            if a.folder_id is None:
                occupied.add(a.sort_id)
        for f in self.folders.values():
            occupied.add(f.sort_id)
        if exclude is not None:
            occupied.discard(exclude)
        base = page * self._page_size
        for slot in range(self._page_size):
            if base + slot not in occupied:
                return base + slot
        # Page full — spill to next page
        return self._next_slot_on_page(page + 1)

    def _folder_dict(self, folder) -> dict:
        """Folder dict with first 4 child app dicts embedded as 'children'."""
        children = [
            {**self.apps[aid].to_dict(), "type": "app"}
            for aid in folder.app_ids[:4]
            if aid in self.apps
        ]
        return {**folder.to_dict(), "type": "folder", "children": children}

    def _repair_folder_ids(self) -> None:
        for folder_id, folder in list(self.folders.items()):
            folder.app_ids = [aid for aid in folder.app_ids if aid in self.apps]
            if not folder.app_ids:
                del self.folders[folder_id]
                continue
            for app_id in folder.app_ids:
                app = self.apps.get(app_id)
                if app and app.folder_id is None:
                    app.folder_id = folder_id

    def _ensure_sort_ids(self) -> None:
        all_items = [a for a in self.apps.values() if a.folder_id is None] + list(
            self.folders.values()
        )
        seen: set[int] = set()
        max_id = max((i.sort_id for i in all_items), default=-1)
        for item in sorted(all_items, key=lambda x: x.sort_id):
            if item.sort_id in seen:
                max_id += 1
                item.sort_id = max_id
            seen.add(item.sort_id)
```

---

## /home/user/Projects/linxpad/src/linxpad/services/icons.py

```python
#  _     _                            _
# | |   (_)_ __ __  ___ __   __ _  __| |
# | |   | | '_ \\ \/ / '_ \ / _` |/ _` |
# | |___| | | | |>  <| |_) | (_| | (_| |
# |_____|_|_| |_/_/\_\ .__/ \__,_|\__,_|
#                    |_|
#
# Author: Andrianos Papamarkou
# Licence: GPL3
# https://github.com/apapamarkou/linxpad
# https://apapamarkou.github.io/linxpad/

import logging
import os

logger = logging.getLogger(__name__)

_SEARCH_PATHS = [
    "/usr/share/icons",
    "/usr/share/pixmaps",
    os.path.expanduser("~/.local/share/icons"),
]
_THEME_PRIORITY = {"breeze-dark": 4, "breeze": 3, "hicolor": 2}
_VALID_EXTS = {".png", ".svg", ".svgz"}


class IconResolver:
    def __init__(self):
        self._cache: dict = {}

    def resolve(self, icon_name: str | None) -> str | None:
        if not icon_name:
            return None
        if icon_name in self._cache:
            return self._cache[icon_name]

        result = self._find(icon_name)
        self._cache[icon_name] = result
        return result

    def _find(self, icon_name: str) -> str | None:
        if os.path.isabs(icon_name) and os.path.exists(icon_name):
            return icon_name

        candidates = []
        for base in _SEARCH_PATHS:
            if not os.path.isdir(base):
                continue
            for root, _, files in os.walk(base):
                for f in files:
                    stem, ext = os.path.splitext(f)
                    if stem != icon_name or ext.lower() not in _VALID_EXTS:
                        continue
                    full = os.path.join(root, f)
                    theme_score = next(
                        (p for t, p in _THEME_PRIORITY.items() if f"/{t}/" in full), 0
                    )
                    size = self._parse_size(full)
                    candidates.append((size, theme_score, full))

        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return candidates[0][2]

    @staticmethod
    def _parse_size(path: str) -> int:
        parts = path.split(os.sep)
        if "scalable" in parts:
            return 9999
        for p in parts:
            if "x" in p:
                a = p.split("x")[0]
                if a.isdigit():
                    return int(a)
            elif p.isdigit():
                return int(p)
        return 0
```

---

## /home/user/Projects/linxpad/tests/ — directory listing

The `tests/` directory exists but contains no files.
