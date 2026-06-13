#!/usr/bin/env python3
"""CSDN 知识库命令行工具。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from indexer import CSDNCrawler, CSDNStore, DEFAULT_HOME_URL, DEFAULT_INDEX_PATH, DEFAULT_STATE_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CSDN 博客知识库工具（默认优先面向 weixin_57166741）")
    parser.add_argument("--home", default=DEFAULT_HOME_URL, help="CSDN 主页 URL（默认指向 weixin_57166741）")
    parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH), help="索引文件路径")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH), help="状态文件路径")

    sub = parser.add_subparsers(dest="command", required=True)

    links = sub.add_parser("links", help="抓取并列出该博主的所有文章链接")
    links.add_argument("--max-pages", type=int, default=20, help="最多遍历列表页数量")
    links.add_argument("--json", action="store_true", help="以 JSON 数组输出")

    crawl = sub.add_parser("crawl", help="抓取并重建索引")
    crawl.add_argument("--max-articles", type=int, default=30, help="最多抓取文章数量")
    crawl.add_argument("--max-pages", type=int, default=5, help="最多遍历列表页数量")

    query = sub.add_parser("query", help="搜索索引")
    query.add_argument("keyword", help="搜索关键词")
    query.add_argument("--limit", type=int, default=5, help="返回结果数量")

    sub.add_parser("stats", help="查看索引状态")
    sub.add_parser("clear", help="清空索引")
    return parser


def cmd_links(args: argparse.Namespace) -> int:
    crawler = CSDNCrawler(home_url=args.home)
    urls = crawler.list_article_links(max_pages=args.max_pages)
    if args.json:
        print(json.dumps(urls, ensure_ascii=False, indent=2))
        return 0

    for index, url in enumerate(urls, start=1):
        print(f"{index}. {url}")
    return 0


def cmd_crawl(args: argparse.Namespace) -> int:
    crawler = CSDNCrawler(home_url=args.home)
    store = CSDNStore(Path(args.index_path), Path(args.state_path))
    articles = crawler.build_index(max_articles=args.max_articles, max_pages=args.max_pages)
    store.save(articles)
    print(
        json.dumps(
            {
                "home": args.home,
                "article_count": len(articles),
                "index_path": args.index_path,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = CSDNStore(Path(args.index_path), Path(args.state_path))
    results = store.search(args.keyword, limit=args.limit)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = CSDNStore(Path(args.index_path), Path(args.state_path))
    records = store.load()
    print(
        json.dumps(
            {
                "index_path": args.index_path,
                "state_path": args.state_path,
                "article_count": len(records),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    store = CSDNStore(Path(args.index_path), Path(args.state_path))
    store.clear()
    print(json.dumps({"cleared": True}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "links":
        return cmd_links(args)
    if args.command == "crawl":
        return cmd_crawl(args)
    if args.command == "query":
        return cmd_query(args)
    if args.command == "stats":
        return cmd_stats(args)
    if args.command == "clear":
        return cmd_clear(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
