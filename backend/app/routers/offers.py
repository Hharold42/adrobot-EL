"""Прокси к справочнику офферов Keitaro (для выпадающих списков на фронте)
и проверка доступности Keitaro API."""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_keitaro
from ..keitaro import KeitaroClient, KeitaroError
from ..schemas import CountryOut, OfferOut

router = APIRouter(prefix="/api", tags=["offers"])


@router.get("/offers", response_model=list[OfferOut])
async def list_offers(
    search: str = Query(default="", description="Подстрока в названии или id оффера"),
    client: KeitaroClient = Depends(get_keitaro),
) -> list[OfferOut]:
    try:
        offers = await client.list_offers()
    except KeitaroError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    needle = search.strip().lower()
    result = []
    for offer in offers:
        if offer.get("state") != "active":
            continue
        if needle and needle not in offer["name"].lower() and needle != str(offer["id"]):
            continue
        result.append(
            OfferOut(
                id=offer["id"],
                name=offer["name"],
                country=offer.get("country") or [],
                payout_value=offer.get("payout_value", 0),
                payout_currency=offer.get("payout_currency", "USD"),
                state=offer["state"],
            )
        )
    return result


@router.get("/offers/countries", response_model=list[CountryOut])
async def list_countries(
    client: KeitaroClient = Depends(get_keitaro),
) -> list[CountryOut]:
    """Список гео, собранный из офферов (в Keitaro нет справочника стран).

    Регион берём из названия группы офферов (Latam / Europe / Asia).
    """
    try:
        offers, groups = await client.list_offers(), await client.list_offer_groups()
    except KeitaroError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    group_names = {group["id"]: group["name"] for group in groups}
    countries: dict[str, CountryOut] = {}
    for offer in offers:
        if offer.get("state") != "active":
            continue
        country = offer.get("country") or []
        if not country:
            continue
        code = country[0]
        entry = countries.setdefault(
            code,
            CountryOut(
                code=code,
                offers_count=0,
                region=group_names.get(offer.get("group_id"), ""),
            ),
        )
        entry.offers_count += 1
    return sorted(countries.values(), key=lambda c: (c.region, c.code))


@router.get("/keitaro/status")
async def keitaro_status(
    client: KeitaroClient = Depends(get_keitaro),
) -> dict:
    """Проверяет, что Keitaro API доступен с текущим ключом.

    Используется индикатором в сайдбаре и страницей настроек.
    Всегда отвечает 200, результат — в поле ok.
    """
    try:
        await client.list_domains()
    except KeitaroError as exc:
        return {"ok": False, "detail": str(exc)}
    return {"ok": True}
