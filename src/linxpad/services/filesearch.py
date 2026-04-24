import os
from collections.abc import Iterator


def search_home(query: str, max_results: int = 50) -> Iterator[dict]:
    """Yield file/folder matches under ~ (non-hidden only)."""
    home = os.path.expanduser("~")
    query_lower = query.lower()
    count = 0

    for root, dirs, files in os.walk(home):
        # Skip hidden directories in-place so os.walk doesn't descend into them
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for name in dirs + files:
            if name.startswith("."):
                continue
            if query_lower in name.lower():
                full = os.path.join(root, name)
                yield {
                    "name": name,
                    "path": full,
                    "is_dir": os.path.isdir(full),
                }
                count += 1
                if count >= max_results:
                    return
