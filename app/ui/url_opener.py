"""
Safe opening of external links.

Only http/https links are opened in the system browser. Anything else
(file:, javascript:, data:, ...) is rejected, because the catalog and the
GitHub API are external data sources and must not be able to run local
commands or open arbitrary local files.
"""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


ALLOWED_SCHEMES = {"http", "https"}


def sanitize_external_url(url: object) -> QUrl | None:
    """
    Returns a QUrl if `url` is a valid http(s) link, otherwise None.
    """
    if not isinstance(url, str):
        return None

    value = url.strip()
    if not value:
        return None

    qurl = QUrl(value)
    if not qurl.isValid() or qurl.scheme().lower() not in ALLOWED_SCHEMES:
        print(f"[url] Refused to open a non-http(s) link: {value!r}")
        return None

    return qurl


def open_external_url(url: object) -> bool:
    """
    Opens an external link in the default browser.

    Returns True if the link was valid and handed over to the OS.
    """
    qurl = sanitize_external_url(url)
    if qurl is None:
        return False

    return QDesktopServices.openUrl(qurl)
