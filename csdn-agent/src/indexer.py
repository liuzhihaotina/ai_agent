"""CSDN 博客抓取与索引。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from utils import extract_text_from_html, guess_summary, is_article_url, is_target_blog_url, normalize_url, unique_preserve_order


DEFAULT_HOME_URL = "https://blog.csdn.net/weixin_57166741"
DEFAULT_STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
DEFAULT_INDEX_PATH = DEFAULT_STORAGE_DIR / "csdn_index.json"
DEFAULT_STATE_PATH = DEFAULT_STORAGE_DIR / "crawl_state.json"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


LINK_RE = re.compile(r'<a\s+[^>]*href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<text>[\s\S]*?)</a>', re.IGNORECASE)
TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
META_DESC_RE = re.compile(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](?P<content>[^"\']+)["\'][^>]*>', re.IGNORECASE)
META_OG_DESC_RE = re.compile(r'<meta\s+[^>]*property=["\']og:description["\'][^>]*content=["\'](?P<content>[^"\']+)["\'][^>]*>', re.IGNORECASE)
META_OG_TITLE_RE = re.compile(r'<meta\s+[^>]*property=["\']og:title["\'][^>]*content=["\'](?P<content>[^"\']+)["\'][^>]*>', re.IGNORECASE)
PAGE_RE = re.compile(r"(?:\?|&)(?:page|p)=([0-9]+)", re.IGNORECASE)


@dataclass
class ArticleRecord:
    url: str
    title: str
    summary: str
    content: str
    source: str = "csdn"

    def to_dict(self) -> dict:
        return asdict(self)


class FetchError(RuntimeError):
    pass


class CSDNCrawler:
    def __init__(self, home_url: str = DEFAULT_HOME_URL, user_agent: str = DEFAULT_USER_AGENT):
        self.home_url = home_url.rstrip("/")
        self.user_agent = user_agent

    def fetch_html(self, url: str, timeout: int = 20) -> str:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except HTTPError as exc:
            raise FetchError(f"HTTP {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            raise FetchError(str(exc.reason)) from exc
        except Exception as exc:
            raise FetchError(str(exc)) from exc

    def extract_title(self, html: str, fallback: str = "") -> str:
        for pattern in (META_OG_TITLE_RE, TITLE_RE):
            match = pattern.search(html)
            if match:
                title = extract_text_from_html(match.group(1) if pattern is TITLE_RE else match.group("content"))
                if title:
                    return title
        return fallback

    def extract_description(self, html: str) -> str:
        for pattern in (META_OG_DESC_RE, META_DESC_RE):
            match = pattern.search(html)
            if match:
                desc = extract_text_from_html(match.group("content"))
                if desc:
                    return desc
        return ""

    def extract_article_links(self, html: str) -> list[str]:
        links = []
        for match in LINK_RE.finditer(html):
            href = match.group("href").strip()
            if not href:
                continue
            url = normalize_url(self.home_url, href)
            if is_article_url(url) and is_target_blog_url(url, self.home_url):
                links.append(url)
        return unique_preserve_order(links)

    def extract_listing_links(self, html: str) -> list[str]:
        links = []
        for match in LINK_RE.finditer(html):
            href = match.group("href").strip()
            if not href:
                continue
            url = normalize_url(self.home_url, href)
            if is_target_blog_url(url, self.home_url) and not is_article_url(url):
                links.append(url)
        return unique_preserve_order(links)

    def _guess_page_url(self, page_num: int) -> str:
        if page_num <= 1:
            return self.home_url
        return f"{self.home_url}/article/list/{page_num}"

    def extract_pagination_links(self, html: str) -> list[str]:
        links = []
        for match in LINK_RE.finditer(html):
            href = match.group("href").strip()
            if not href:
                continue
            url = normalize_url(self.home_url, href)
            if not is_target_blog_url(url, self.home_url):
                continue
            if is_article_url(url):
                continue
            if "/article/list/" in urlparse(url).path or url == self.home_url:
                links.append(url)
        for match in PAGE_RE.finditer(html):
            page_num = int(match.group(1))
            if page_num > 1:
                links.append(self._guess_page_url(page_num))
        return unique_preserve_order(links)

    def extract_main_content(self, html: str) -> str:
        candidates = []
        for pattern in (
            re.compile(r'<article[^>]*>([\s\S]*?)</article>', re.IGNORECASE),
            re.compile(r'<div[^>]*class=["\'][^"\']*(?:article_content|blog-content|blog-body|markdown-view)[^"\']*["\'][^>]*>([\s\S]*?)</div>', re.IGNORECASE),
            re.compile(r'<div[^>]*id=["\']content_views["\'][^>]*>([\s\S]*?)</div>', re.IGNORECASE),
        ):
            match = pattern.search(html)
            if match:
                candidates.append(match.group(1))
        if candidates:
            return extract_text_from_html(candidates[0])
        return extract_text_from_html(html)

    def fetch_article(self, url: str) -> ArticleRecord:
        html = self.fetch_html(url)
        title = self.extract_title(html, fallback=url)
        content = self.extract_main_content(html)
        summary = self.extract_description(html) or guess_summary(content)
        return ArticleRecord(url=url, title=title, summary=summary, content=content)

    def crawl_home(self, max_pages: int = 5) -> list[str]:
        start = self.home_url
        visited = set()
        to_visit = [start]
        article_urls: list[str] = []

        while to_visit and len(visited) < max_pages:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)
            try:
                html = self.fetch_html(current)
            except FetchError:
                continue

            article_urls.extend(self.extract_article_links(html))
            for link in self.extract_listing_links(html):
                if link not in visited and link not in to_visit:
                    if len(to_visit) + len(visited) < max_pages * 3:
                        to_visit.append(link)
            for link in self.extract_pagination_links(html):
                if link not in visited and link not in to_visit:
                    if len(to_visit) + len(visited) < max_pages * 3:
                        to_visit.append(link)

        return unique_preserve_order(article_urls)

    def list_article_links(self, max_pages: int = 5) -> list[str]:
        return self.crawl_home(max_pages=max_pages)

    def build_index(self, max_articles: int = 30, max_pages: int = 5) -> list[ArticleRecord]:
        articles: list[ArticleRecord] = []
        urls = self.crawl_home(max_pages=max_pages)
        for url in urls[:max_articles]:
            try:
                articles.append(self.fetch_article(url))
            except FetchError:
                continue
        return articles


class CSDNStore:
    def __init__(self, index_path: Path = DEFAULT_INDEX_PATH, state_path: Path = DEFAULT_STATE_PATH):
        self.index_path = Path(index_path)
        self.state_path = Path(state_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def save(self, records: Iterable[ArticleRecord]) -> None:
        payload = [record.to_dict() for record in records]
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.state_path.write_text(
            json.dumps({"article_count": len(payload)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def search(self, query: str, limit: int = 5) -> list[dict]:
        query = (query or "").strip().lower()
        if not query:
            return []

        records = self.load()
        scored = []
        for record in records:
            title = str(record.get("title", ""))
            summary = str(record.get("summary", ""))
            content = str(record.get("content", ""))
            haystack = f"{title}\n{summary}\n{content}".lower()
            score = 0
            for token in re.findall(r"[\w\u4e00-\u9fff]+", query):
                if token and token in haystack:
                    score += 1
            if query in haystack:
                score += 3
            if score:
                scored.append((score, record))

        scored.sort(key=lambda item: (-item[0], str(item[1].get("title", ""))))
        return [item[1] for item in scored[:limit]]

    def clear(self) -> None:
        if self.index_path.exists():
            self.index_path.unlink()
        if self.state_path.exists():
            self.state_path.unlink()
