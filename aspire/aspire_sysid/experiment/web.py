"""Web access in real runs: ``web_fetch`` over HTTP(S), ``web_search`` by the model's vendor.

The agent has web access. The turn loop takes its web backends by injection
(:class:`aspire_sysid.agent.tools.WebBackends`); without a backend a web tool tells the agent that
it is unavailable. The experiment runner gives real runs the fetch backend :func:`urllib_fetch`
(Python standard library; the tool itself refuses addresses that contain a denied substring, such
as the address of the harness's repository, before the backend is called).

``web_search`` has no backend of the harness. With a model of OpenAI the tool is offered as the
vendor's built-in web search tool of the Responses API (:data:`aspire_sysid.agent.providers.OPENAI_WEB_SEARCH_TOOL`): the vendor executes the searches
inside a response, the harness records every search action with its query and sources and
charges the vendor's fee per call. With any other provider the tool is a function tool without a
backend and reports that it is unavailable. Dry runs and tests make no network request.
"""

from __future__ import annotations

import html
import re
import urllib.request

from ..agent.tools import WebBackends

__all__ = ["MAX_FETCH_BYTES", "USER_AGENT", "VENDOR_WEB_SEARCH", "urllib_fetch", "real_web_backends", "web_backends_record"]

MAX_FETCH_BYTES = 2_000_000
"""Bytes read from one fetched resource; the rest is not read."""

USER_AGENT = "aspire-sysid (research harness; web_fetch tool)"

_SCRIPT_STYLE = re.compile(r"<(script|style|noscript)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_BLANKS = re.compile(r"\n\s*\n\s*\n+")


def _text_of_html(page: str) -> str:
    t = _SCRIPT_STYLE.sub(" ", page)
    t = re.sub(r"<(br|p|div|li|tr|h[1-6])\b[^>]*>", "\n", t, flags=re.IGNORECASE)
    t = html.unescape(_TAG.sub(" ", t))
    t = "\n".join(" ".join(line.split()) for line in t.splitlines())
    return _BLANKS.sub("\n\n", t).strip()


def urllib_fetch(url: str, timeout_s: float) -> str:
    """Fetch ``url`` and return its text. An HTML page is reduced to its visible text;
    other text types are returned as decoded; binary content is described, not returned."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=max(1.0, float(timeout_s))) as resp:  # noqa: S310 - http(s) only, checked by the tool
        ctype = resp.headers.get("Content-Type", "")
        blob = resp.read(MAX_FETCH_BYTES + 1)
    truncated = len(blob) > MAX_FETCH_BYTES
    blob = blob[:MAX_FETCH_BYTES]
    charset = "utf-8"
    m = re.search(r"charset=([\w.-]+)", ctype, re.IGNORECASE)
    if m:
        charset = m.group(1)
    if not (ctype.startswith("text/") or "json" in ctype or "xml" in ctype or not ctype):
        return f"[{len(blob)} bytes of content type {ctype!r}; not text]"
    text = blob.decode(charset, errors="replace")
    if "html" in ctype.lower() or text.lstrip()[:15].lower().startswith(("<!doctype html", "<html")):
        text = _text_of_html(text)
    return text + (f"\n[... only the first {MAX_FETCH_BYTES} bytes were read]" if truncated else "")


def real_web_backends() -> WebBackends:
    """The web backends of a real run: fetch only; the search is the vendor's (module docstring). """
    return WebBackends(fetch=urllib_fetch, search=None)


VENDOR_WEB_SEARCH = {
    "openai": "provided by the vendor: the built-in web search tool of the OpenAI Responses API, executed by the vendor "
              "inside a response; the harness records each search action with its query and sources",
}
"""Vendors whose adapter offers the vendor's own web search tool, with the statement for the record."""


def web_backends_record(backends: WebBackends | None, vendor: str | None = None) -> dict[str, str]:
    """What the run record states about web access. ``vendor`` is the vendor of
    the run's provider (``scripted`` for the scripted agent)."""
    b = backends or WebBackends()
    if b.search is not None:
        search = "available (injected backend)"
    else:
        search = VENDOR_WEB_SEARCH.get(str(vendor), "unavailable: the provider of this run has no web search")
    return {
        "web_fetch": "available (Python urllib, text of the resource)" if b.fetch is not None else "unavailable: no backend configured",
        "web_search": search,
    }
