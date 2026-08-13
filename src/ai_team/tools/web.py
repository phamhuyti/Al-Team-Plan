"""Web search tool for Researcher (MCP V2 preview: web).

Default backend is DuckDuckGo HTML (no API key). Failures degrade to [] so
offline / NAS environments still complete research from local context.
"""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse

import httpx

Fetcher = Callable[[str, int], list[dict[str, str]]]


class _DDGParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result_link = False
        self._in_snippet = False
        self._current: dict[str, str] | None = None
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: (v or "") for k, v in attrs}
        classes = attrs_dict.get("class", "")
        if tag == "a" and "result__a" in classes.split():
            href = attrs_dict.get("href", "")
            url = _unwrap_ddg_url(href)
            self._current = {"title": "", "url": url, "snippet": ""}
            self._title_parts = []
            self._in_result_link = True
        elif tag == "a" and "result__snippet" in classes.split():
            self._in_snippet = True
            self._snippet_parts = []
        elif tag in {"td", "div"} and "result__snippet" in classes.split():
            self._in_snippet = True
            self._snippet_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_result_link and self._current is not None:
            self._current["title"] = _clean("".join(self._title_parts))
            self._in_result_link = False
            if self._current["url"] and self._current["title"]:
                self.results.append(self._current)
            self._current = None
        if tag in {"a", "td", "div"} and self._in_snippet:
            snippet = _clean("".join(self._snippet_parts))
            if self.results and not self.results[-1].get("snippet"):
                self.results[-1]["snippet"] = snippet
            self._in_snippet = False

    def handle_data(self, data: str) -> None:
        if self._in_result_link:
            self._title_parts.append(data)
        elif self._in_snippet:
            self._snippet_parts.append(data)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _unwrap_ddg_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


def search_duckduckgo(query: str, max_results: int = 5, timeout: float = 15.0) -> list[dict[str, str]]:
    query = (query or "").strip()
    if not query:
        return []
    headers = {
        "User-Agent": "ai-team-researcher/0.1 (+https://github.com/phamhuyti/Al-Team-Plan)",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
        )
        response.raise_for_status()
        parser = _DDGParser()
        parser.feed(response.text)
        hits = parser.results[: max(1, max_results)]
        if hits:
            return hits
        # Fallback: Instant Answer API (often sparse, but no HTML dependency).
        ia = client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
        )
        ia.raise_for_status()
        data = ia.json()
        return _instant_answer_hits(data, query, max_results)


def _instant_answer_hits(data: dict[str, Any], query: str, max_results: int) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    abstract = (data.get("AbstractText") or "").strip()
    abstract_url = (data.get("AbstractURL") or "").strip()
    heading = (data.get("Heading") or query).strip()
    if abstract:
        hits.append({"title": heading, "url": abstract_url or "https://duckduckgo.com", "snippet": abstract})
    for topic in data.get("RelatedTopics") or []:
        if len(hits) >= max_results:
            break
        if isinstance(topic, dict) and topic.get("Text"):
            hits.append(
                {
                    "title": str(topic.get("Text", ""))[:80],
                    "url": str(topic.get("FirstURL") or ""),
                    "snippet": str(topic.get("Text") or ""),
                }
            )
        elif isinstance(topic, dict) and isinstance(topic.get("Topics"), list):
            for nested in topic["Topics"]:
                if len(hits) >= max_results:
                    break
                if isinstance(nested, dict) and nested.get("Text"):
                    hits.append(
                        {
                            "title": str(nested.get("Text", ""))[:80],
                            "url": str(nested.get("FirstURL") or ""),
                            "snippet": str(nested.get("Text") or ""),
                        }
                    )
    return hits[:max_results]


def mock_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    q = (query or "topic").strip() or "topic"
    return [
        {
            "title": f"Overview: {q}",
            "url": "https://example.com/docs/overview",
            "snippet": f"Established patterns and trade-offs for {q}. Prefer simple, testable designs.",
        },
        {
            "title": f"Comparison notes for {q}",
            "url": "https://example.com/docs/compare",
            "snippet": f"Common options for {q} differ mainly in operational complexity and maturity.",
        },
    ][: max(1, max_results)]


class WebSearchTools:
    def __init__(
        self,
        *,
        enabled: bool = True,
        backend: str = "duckduckgo",
        max_results: int = 5,
        fetcher: Fetcher | None = None,
    ) -> None:
        self.enabled = enabled
        self.backend = (backend or "duckduckgo").lower()
        self.max_results = max_results
        self._fetcher = fetcher

    def search(self, query: str, max_results: int | None = None) -> list[dict[str, str]]:
        limit = max_results if max_results is not None else self.max_results
        if not self.enabled or self.backend in {"off", "none", "disabled"}:
            return []
        if self._fetcher is not None:
            return self._fetcher(query, limit)
        if self.backend == "mock":
            return mock_search(query, limit)
        try:
            return search_duckduckgo(query, max_results=limit)
        except Exception:  # noqa: BLE001 — research must degrade offline
            if self.backend == "duckduckgo":
                return []
            return mock_search(query, limit)

    def format_evidence(self, hits: list[dict[str, str]]) -> list[str]:
        evidence: list[str] = []
        for hit in hits:
            title = hit.get("title") or "result"
            url = hit.get("url") or ""
            snippet = hit.get("snippet") or ""
            evidence.append(f"{title} — {snippet} ({url})".strip())
        return evidence
