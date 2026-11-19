# Bugfix Requirements Document

## Introduction

Icons in the LinxPad launcher grid disappear intermittently. The icon pipeline flows from desktop scanning, through icon resolution and caching, into pixmap loading and rendering. Several defects along this pipeline cause icons to vanish instead of degrading gracefully to a fallback:

1. The icon loader trusts a cached resolved path without re-validating that the file still exists, so when a theme is uninstalled or a package is updated, it returns a null pixmap and renders blank.
2. SVG/SVGZ icons silently become null pixmaps when the Qt SVG image format plugin is not installed, instead of falling back.
3. A filesystem rescan triggered during a package update deletes apps whose `.desktop` files are transiently unavailable, so icons disappear and later reappear in the wrong grid position.
4. Dragging an item onto an already-full page overflows the layout into the next page instead of being blocked.
5. The icon size parser misparses path components such as "2x-retina" and selects the wrong-sized icon.

The impact is that users see icons disappear and reappear in unexpected places, undermining trust in the launcher. The fixes must ensure icons never render blank (always falling back to a letter-avatar), apps are retained across transient `.desktop` unavailability, drag moves to full pages are blocked, and icon size selection is correct.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the icon resolver returns a cached path for an app's icon name and the file at that cached path no longer exists on disk (for example, after a theme uninstall or package update), THEN the icon loader returns a null pixmap — a QPixmap whose isNull() returns True — instead of a fallback, and the icon area renders with no pixmap content.

1.2 WHEN the icon loader loads a pixmap from a resolved icon path ending with `.svg` or `.svgz` (case-insensitive) whose file exists on disk, and `QPixmap(path).isNull()` returns True for that path (indicating the Qt SVG image format plugin is unavailable), THEN the icon loader returns that null pixmap to the grid renderer without checking `.isNull()` before returning, so the grid cell renders no icon image because the paint guard skips null pixmaps, and the icon disappears instead of showing the letter-avatar fallback.

1.3 WHEN a `.desktop` file is transiently unavailable during a package update and a filesystem rescan is triggered, THEN the app is removed from the saved state — its UUID is discarded, its grid page is compacted, and its icon disappears; when the file reappears the app is re-added with a new UUID at a different grid position (max_sort + 1).

1.4 WHEN an item is dragged from a source page onto a target page on which the dragged item is not already present and the number of items on the target page equals page_size, THEN the reorder inserts the item anyway, because the capacity check compares the item count against page_size using a strictly-greater-than test that misses the exactly-full case, and one of the reassigned sort positions overflows past the target page's slot range into the next page's slots, corrupting the grid layout.

1.5 WHEN an icon path contains, before any "NxN" size directory, a path component that begins with a digit sequence followed by "x" and whose remainder after "x" is not purely digits (for example "2x-retina"), THEN the size parser returns the integer value of that leading digit sequence instead of the size of the "NxN" size directory.

### Expected Behavior (Correct)

2.1 IF the icon resolver returns a path for an app's icon name and the file at that path does not exist on disk, THEN the system SHALL render the letter-avatar placeholder for that app — a non-null pixmap displaying the uppercased first character of the app's name, or "?" when the name is empty or absent — instead of a null pixmap.

2.2 WHEN the system renders an app item, THEN the system SHALL produce a non-null pixmap — a QPixmap whose isNull() returns False — for that item, regardless of whether the item's icon path or icon name is valid, absent, or stale, so the icon area never renders blank.

2.3 IF an app's icon path is absent and the app's icon name resolves through the icon resolver to a path whose file does not exist on disk, THEN the system SHALL render the letter-avatar placeholder for that app, and the rendered pixmap SHALL be non-null.

2.4 WHEN the icon loader loads a pixmap from a resolved icon path ending with `.svg` or `.svgz` (case-insensitive) whose file exists on disk, IF `QPixmap(path).isNull()` returns True for that path (indicating the Qt SVG image format plugin is unavailable), THEN the icon loader SHALL check `.isNull()` on the loaded pixmap before returning it and, on True, substitute the letter-avatar fallback — a non-null pixmap drawn from the uppercased first character of the application name — so that the pixmap returned by the icon loader is never null for an application item.

2.5 WHEN a `.desktop` file is transiently unavailable — absent from scan results for fewer than N consecutive scans (where N is configurable with a default of 3) — THEN the system SHALL retain the app in state with its identifier, grid position (sort_id), and folder membership unchanged during the grace period, so the app's icon does not disappear.

2.6 WHEN a `.desktop` file has been absent from scan results for N or more consecutive scans (where N is configurable with a default of 3), THEN the system SHALL remove the app from state and compact the grid page.

2.7 WHEN a `.desktop` file reappears in scan results before the consecutive absence count reaches N, THEN the system SHALL reset the consecutive absence count to zero and preserve the app's existing identifier, grid position, and folder membership without modification.

2.8 WHEN an item is dragged from a source page onto a target page on which the dragged item is not already present and the number of items on the target page is greater than or equal to page_size, THEN the system SHALL block the move so that the dragged item remains at its original sort position, no item's sort position is modified, and the grid layout is unchanged.

2.9 WHEN an icon path contains an "NxN" size directory, the size parser SHALL return N as the size, where an "NxN" size directory is a path component consisting of a digit sequence, the character "x", and a second digit sequence of equal value (for example "48x48", "16x16", "32x32"), and N is the integer value of that digit sequence.

2.10 IF an icon path contains a path component that includes the character "x" but is not an "NxN" size directory because the part following "x" is not purely digits (for example "2x-retina"), THEN the size parser SHALL ignore that component when determining the size.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN an icon's resolved path is valid — the file at that path exists on disk and yields a non-null pixmap — THEN the system SHALL CONTINUE TO render the icon from that path.

3.2 WHEN the icon loader loads a pixmap from a resolved icon path ending with `.svg` or `.svgz` (case-insensitive) and `QPixmap(path).isNull()` returns False for that path (indicating the Qt SVG image format plugin is available), THEN the system SHALL CONTINUE TO return the non-null SVG-rendered pixmap for that icon.

3.3 WHEN a `.desktop` file has been absent from scan results for N or more consecutive scans (application permanently uninstalled), THEN the system SHALL CONTINUE TO remove the app from state and compact the grid.

3.4 WHEN an item is dragged from a source page onto a target page on which the dragged item is not already present and the number of items on the target page is less than page_size, THEN the system SHALL CONTINUE TO insert the item and reassign sort positions so that every item on the target page has a sort position within that page's slot range.

3.5 WHEN an icon path contains "scalable" as a path component, the size parser SHALL CONTINUE TO return 9999 as the size, which takes precedence over any "NxN" size directory in the same path.

3.6 WHEN an app has neither a valid icon path (the path is absent or its file does not exist on disk) nor an icon name that resolves to a valid icon, THEN the system SHALL CONTINUE TO render the letter-avatar fallback showing the uppercased first character of the app's name, or "?" when the name is empty or absent.

3.7 WHEN apps are first discovered via scan, THEN the system SHALL CONTINUE TO add them with new identifiers appended after the current maximum sort position.
