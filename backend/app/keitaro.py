"""Асинхронный клиент для Keitaro Admin API v1."""

from typing import Any

import httpx

from .config import get_settings


class KeitaroError(Exception):
    """Ошибка при обращении к Keitaro API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class KeitaroClient:
    """Обёртка над httpx.AsyncClient с заголовком Api-Key.

    Ключ берётся из аргумента (его прислал фронт в заголовке X-Keitaro-Key),
    а если его нет — из настроек (.env).
    """

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._client = httpx.AsyncClient(
            base_url=settings.keitaro_base_url,
            headers={"Api-Key": api_key or settings.keitaro_api_key},
            timeout=30.0,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise KeitaroError(f"Keitaro недоступен: {exc}") from exc
        if response.status_code >= 400:
            raise KeitaroError(
                f"Keitaro вернул {response.status_code}: {response.text[:500]}",
                status_code=response.status_code,
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()

    # --- Справочники -------------------------------------------------

    async def list_offers(self) -> list[dict]:
        return await self._request("GET", "/offers")

    async def get_offer(self, offer_id: int) -> dict:
        return await self._request("GET", f"/offers/{offer_id}")

    async def list_domains(self) -> list[dict]:
        return await self._request("GET", "/domains")

    async def list_campaign_groups(self) -> list[dict]:
        return await self._request("GET", "/groups", params={"type": "campaigns"})

    async def list_offer_groups(self) -> list[dict]:
        return await self._request("GET", "/groups", params={"type": "offers"})

    async def list_traffic_sources(self) -> list[dict]:
        return await self._request("GET", "/traffic_sources")

    async def resolve_defaults(self) -> dict[str, int]:
        """Находит домен, группу кампаний и источник для новых кампаний.

        В эмуляторе каждый ресурс существует в единственном экземпляре,
        поэтому просто берём первый активный из каждого списка.
        """
        domains, groups, sources = (
            await self.list_domains(),
            await self.list_campaign_groups(),
            await self.list_traffic_sources(),
        )
        if not domains or not groups or not sources:
            raise KeitaroError(
                "В Keitaro не найдены домен, группа кампаний или источник трафика"
            )
        return {
            "domain_id": domains[0]["id"],
            "group_id": groups[0]["id"],
            "traffic_source_id": sources[0]["id"],
        }

    # --- Кампании ----------------------------------------------------

    async def create_campaign(
        self, name: str, group_id: int, domain_id: int, traffic_source_id: int
    ) -> dict:
        return await self._request(
            "POST",
            "/campaigns",
            json={
                "name": name,
                "group_id": group_id,
                "domain_id": domain_id,
                "traffic_source_id": traffic_source_id,
                "state": "active",
            },
        )

    async def update_campaign(self, campaign_id: int, payload: dict) -> dict:
        return await self._request("PUT", f"/campaigns/{campaign_id}", json=payload)

    async def list_campaigns(self) -> list[dict]:
        return await self._request("GET", "/campaigns")

    async def get_campaign(self, campaign_id: int) -> dict:
        return await self._request("GET", f"/campaigns/{campaign_id}")

    async def delete_campaign(self, campaign_id: int) -> None:
        await self._request("DELETE", f"/campaigns/{campaign_id}")

    # --- Потоки ------------------------------------------------------

    async def create_geo_stream(
        self, campaign_id: int, geo_code: str, redirect_url: str
    ) -> dict:
        """Поток №1: ловит трафик из указанной страны и уводит на Google."""
        return await self._request(
            "POST",
            "/streams",
            json={
                "campaign_id": campaign_id,
                "name": f"GEO {geo_code} -> Google",
                "position": 1,
                "type": "regular",
                "schema": "redirect",
                "action_type": "http_redirect",
                "action_payload": redirect_url,
                "filters": [
                    {"name": "country", "mode": "accept", "payload": [geo_code]}
                ],
                "landings": [],
                "offers": [],
            },
        )

    async def create_offer_stream(
        self, campaign_id: int, offer_ids: list[int]
    ) -> dict:
        """Поток №2: всё остальное отправляет на выбранные офферы (доли поровну)."""
        return await self._request(
            "POST",
            "/streams",
            json={
                "campaign_id": campaign_id,
                "name": "Offers",
                "position": 2,
                "type": "regular",
                "schema": "landings",
                "landings": [],
                "offers": rebalance_shares(offer_ids),
                "filters": [],
            },
        )

    async def list_campaign_streams(self, campaign_id: int) -> list[dict]:
        return await self._request("GET", f"/campaigns/{campaign_id}/streams")

    async def get_stream(self, stream_id: int) -> dict:
        return await self._request("GET", f"/streams/{stream_id}")

    async def update_stream_offers(
        self, stream_id: int, offers: list[dict]
    ) -> dict:
        """Полностью заменяет список офферов потока.

        offers: [{"offer_id": int, "share": int, "state": "active"}, ...]
        """
        return await self._request(
            "PUT", f"/streams/{stream_id}", json={"offers": offers}
        )


def rebalance_shares(offer_ids: list[int]) -> list[dict]:
    """Раскидывает 100% поровну между офферами.

    Остаток от деления уходит первым офферам, чтобы сумма всегда была 100.
    """
    if not offer_ids:
        return []
    base = 100 // len(offer_ids)
    remainder = 100 % len(offer_ids)
    return [
        {
            "offer_id": offer_id,
            "share": base + (1 if index < remainder else 0),
            "state": "active",
        }
        for index, offer_id in enumerate(offer_ids)
    ]
