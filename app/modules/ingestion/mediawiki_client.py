import asyncio
from typing import Any, cast

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class MediaWikiClient:
    def __init__(self) -> None:
        self.api_url = settings.mediawiki_api_url
        self.delay = settings.crawler_delay_seconds
        self.max_retries = settings.crawler_max_retries
        self.client = httpx.AsyncClient(
            headers={"User-Agent": settings.crawler_user_agent},
            timeout=settings.crawler_timeout_seconds,
        )

    async def _request(self, params: dict[str, str]) -> dict[str, Any]:
        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(self.api_url, params=params)
                response.raise_for_status()
                return cast(dict[str, Any], response.json())
            except httpx.HTTPError as e:
                logger.warning("mediawiki_request_failed", attempt=attempt + 1, error=str(e))
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)
        raise RuntimeError("unreachable")

    async def list_all_pages(self, namespace: int = 0) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        params: dict[str, str] = {
            "action": "query",
            "list": "allpages",
            "apnamespace": str(namespace),
            "aplimit": "max",
            "format": "json",
        }

        while True:
            data = await self._request(params)
            query = data.get("query", {})
            batch = query.get("allpages", [])
            pages.extend(batch)

            if continue_param := data.get("continue", {}).get("apcontinue"):
                params["apcontinue"] = continue_param
            else:
                break

            await asyncio.sleep(self.delay)

        return pages

    async def get_page_html(self, title: str) -> str | None:
        params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
        }

        data = await self._request(params)
        parse = data.get("parse")
        if parse is None:
            return None
        text = parse.get("text", {}).get("*")
        return cast(str | None, text)

    async def get_page_info(self, title: str) -> dict[str, Any] | None:
        params = {
            "action": "query",
            "titles": title,
            "prop": "info|categories",
            "format": "json",
        }

        data = await self._request(params)
        pages = data.get("query", {}).get("pages", {})
        for page_id_str, page_info in pages.items():
            if page_id_str == "-1":
                return None
            return cast(dict[str, Any], page_info)
        return None

    async def list_categories(self) -> list[dict[str, Any]]:
        categories: list[dict[str, Any]] = []
        params: dict[str, str] = {
            "action": "query",
            "list": "allcategories",
            "aclimit": "max",
            "format": "json",
        }

        while True:
            data = await self._request(params)
            batch = data.get("query", {}).get("allcategories", [])
            categories.extend(batch)

            if continue_param := data.get("continue", {}).get("accontinue"):
                params["accontinue"] = continue_param
            else:
                break

            await asyncio.sleep(self.delay)

        return categories

    async def list_category_members(self, category: str) -> list[dict[str, Any]]:
        members: list[dict[str, Any]] = []
        params: dict[str, str] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": "max",
            "format": "json",
        }

        while True:
            data = await self._request(params)
            batch = data.get("query", {}).get("categorymembers", [])
            members.extend(batch)

            if continue_param := data.get("continue", {}).get("cmcontinue"):
                params["cmcontinue"] = continue_param
            else:
                break

            await asyncio.sleep(self.delay)

        return members

    async def close(self) -> None:
        await self.client.aclose()
