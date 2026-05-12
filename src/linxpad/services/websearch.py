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
import re
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _extract_ddg_results(html: str, max_results: int = 15) -> list[dict]:
    """Parse DuckDuckGo HTML search results."""
    results = []

    # DDG wraps each result in <div class="result ..."> or <div class="web-result ...">
    # The result link is in <a class="result__a" href="...">
    # The snippet is in <a class="result__snippet">

    # Extract result blocks
    blocks = re.findall(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>'
        r'.*?<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )

    for href, title_html, snippet_html in blocks:
        if len(results) >= max_results:
            break

        # DDG wraps real URLs in a redirect — unwrap if needed
        url = href
        if href.startswith("//duckduckgo.com/l/"):
            # extract uddg= param
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                from urllib.parse import unquote

                url = unquote(m.group(1))
        elif href.startswith("/"):
            continue  # internal DDG link, skip

        # Strip HTML tags from title and snippet
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet_html).strip()

        if not title or not url.startswith("http"):
            continue

        base = urlparse(url).netloc
        results.append({"title": title, "url": url, "base": base, "description": snippet})

    return results


class WebSearchWorker(QThread):
    results_ready = pyqtSignal(list)  # list of {title, url, base, description}

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self._query = query

    def run(self) -> None:
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(self._query)}"
            req = Request(url, headers=_HEADERS)
            with urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            results = _extract_ddg_results(html)
            self.results_ready.emit(results)
        except Exception:
            logger.debug("Web search failed", exc_info=True)
            self.results_ready.emit([])
