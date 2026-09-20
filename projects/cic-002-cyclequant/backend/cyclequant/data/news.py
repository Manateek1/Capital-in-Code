from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx

from cyclequant.data.base import DataSourceError, SourcePayload
from cyclequant.data.http import request
from cyclequant.models import NewsItem


class GoogleNewsRssProvider:
    name = "google_news_rss"
    category = "news"
    required = False
    stale_after = timedelta(days=2)

    def __init__(self, client: httpx.AsyncClient, retries: int = 3) -> None:
        self.client = client
        self.retries = retries

    async def fetch(self, as_of: datetime, history_days: int) -> SourcePayload:
        query = quote_plus("Bitcoin OR BTC when:2d")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        response = await request(
            self.client,
            self.name,
            "GET",
            url,
            headers={"User-Agent": "CycleQuant/0.1"},
            retries=self.retries,
        )
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc:
            raise DataSourceError(self.name, "invalid RSS XML") from exc
        items: list[NewsItem] = []
        seen: set[tuple[str, str]] = set()
        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published_text = item.findtext("pubDate")
            source_node = item.find("source")
            source = (
                source_node.text.strip()
                if source_node is not None and source_node.text
                else "Unknown"
            )
            if not title or not link or not published_text:
                continue
            published_at = parsedate_to_datetime(published_text).astimezone(UTC)
            if published_at > as_of or as_of - published_at > timedelta(days=3):
                continue
            key = (title.casefold(), source.casefold())
            if key in seen:
                continue
            seen.add(key)
            items.append(
                NewsItem(
                    title=title,
                    source=source,
                    url=link,
                    published_at=published_at,
                )
            )
            if len(items) == 20:
                break
        if not items:
            raise DataSourceError(self.name, "no recent Bitcoin headlines")
        return SourcePayload(
            source=self.name,
            category=self.category,
            observed_at=max(item.published_at for item in items),
            news=items,
            metadata={"item_count": len(items)},
        )
