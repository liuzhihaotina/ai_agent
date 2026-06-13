"""CSDN 知识库通用工具。"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import urljoin, urlparse


_WHITESPACE_RE = re.compile(r"\s+")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)[\s\S]*?</\1>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []
        self._skip_stack: List[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_stack.append(tag.lower())

    def handle_endtag(self, tag: str):
        if self._skip_stack and self._skip_stack[-1] == tag.lower():
            self._skip_stack.pop()

    def handle_data(self, data: str):
        if not self._skip_stack:
            data = data.strip()
            if data:
                self._parts.append(data)

    def get_text(self) -> str:
        return _WHITESPACE_RE.sub(" ", " ".join(self._parts)).strip()


def normalize_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href)


def same_domain(url: str, base_url: str) -> bool:
    return urlparse(url).netloc.lower() == urlparse(base_url).netloc.lower()


def get_blog_slug(home_url: str) -> str:
    path = urlparse(home_url).path.strip("/")
    if not path:
        return ""
    return path.split("/")[0].strip().lower()


def is_target_blog_url(url: str, home_url: str) -> bool:
    parsed = urlparse(url)
    slug = get_blog_slug(home_url)
    netloc = parsed.netloc.lower()

    if not slug:
        return same_domain(url, home_url)

    if netloc == "blog.csdn.net":
        return parsed.path.lower().startswith(f"/{slug}")

    if netloc.endswith(".blog.csdn.net"):
        return netloc.startswith(f"{slug}.")

    return False


def is_article_url(url: str) -> bool:
    parsed = urlparse(url)
    return "/article/details/" in parsed.path


def is_probably_listing_url(url: str, home_url: str) -> bool:
    if not same_domain(url, home_url):
        return False

    if is_article_url(url):
        return False

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    home_path = urlparse(home_url).path.rstrip("/")

    if not path:
        return True
    if path == home_path:
        return True
    if "/article/list/" in path:
        return True
    if "/category/" in path or "/tag/" in path or "/archive/" in path:
        return True
    if "page=" in parsed.query:
        return True
    return False


def clean_html_text(html: str) -> str:
    html = _SCRIPT_STYLE_RE.sub(" ", html)
    html = _TAG_RE.sub(" ", html)
    html = html.replace("&nbsp;", " ")
    html = html.replace("&amp;", "&")
    html = html.replace("&lt;", "<")
    html = html.replace("&gt;", ">")
    html = html.replace("&quot;", '"')
    html = html.replace("&#39;", "'")
    return _WHITESPACE_RE.sub(" ", html).strip()


def extract_text_from_html(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return clean_html_text(html)
    text = parser.get_text()
    return text if text else clean_html_text(html)


def truncate_text(text: str, limit: int = 220) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def guess_summary(text: str, limit: int = 220) -> str:
    if not text:
        return ""
    return truncate_text(text, limit=limit)


def unique_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
