"""Логика редактора потоков: черновики, веса, пины, публикация, синхронизация.

Состояние оффера в потоке хранится в двух «слоях»:
  * черновик (status, share) — то, что видит пользователь в обёртке;
  * опубликованное (in_keitaro, published_share) — то, что сейчас в Keitaro.
Пока слои расходятся, поток «грязный» (жёлтый в UI). Push публикует черновик
в Keitaro, Cancel откатывает черновик к опубликованному состоянию.
"""

from sqlalchemy.orm import Session

from .keitaro import KeitaroClient
from .models import Campaign, Stream, StreamOffer

ACTIVE = "active"
REMOVED = "removed"


class StreamRuleError(ValueError):
    """Нарушено правило распределения весов (превращается в HTTP 400)."""


def active_offers(stream: Stream) -> list[StreamOffer]:
    return [item for item in stream.offers if item.status == ACTIVE]


def is_dirty(stream: Stream) -> bool:
    """Есть ли неопубликованные изменения в потоке."""
    for item in stream.offers:
        if (item.status == ACTIVE) != item.in_keitaro:
            return True
        if item.status == ACTIVE and item.share != item.published_share:
            return True
    return False


def is_editable(stream: Stream) -> bool:
    """Редактируем только поток с офферами; остальные показываем как есть."""
    return stream.schema == "landings" or bool(stream.offers)


def recalc_shares(stream: Stream) -> None:
    """Пересчитывает веса: запиненные не трогаем, остаток делим поровну.

    Удалённые офферы получают 0%. Остаток от деления достаётся первым
    незапиненным офферам, чтобы сумма всегда была ровно 100.
    """
    for item in stream.offers:
        if item.status == REMOVED:
            item.share = 0
            item.pinned = False

    active = active_offers(stream)
    if not active:
        return

    pinned = [item for item in active if item.pinned]
    free = [item for item in active if not item.pinned]
    pinned_sum = sum(item.share for item in pinned)

    if not free:
        if pinned_sum != 100:
            raise StreamRuleError(
                f"Все веса запинены, а их сумма {pinned_sum}% вместо 100%. "
                "Снимите пин хотя бы с одного оффера"
            )
        return

    rest = 100 - pinned_sum
    if rest < 0:
        raise StreamRuleError(
            f"Сумма запиненных весов {pinned_sum}% превышает 100%"
        )
    base, extra = divmod(rest, len(free))
    for index, item in enumerate(free):
        item.share = base + (1 if index < extra else 0)


# --- Операции черновика -------------------------------------------------


def _find(stream: Stream, offer_id: int) -> StreamOffer | None:
    return next((item for item in stream.offers if item.offer_id == offer_id), None)


def add_offer(stream: Stream, offer_id: int) -> None:
    """Добавляет оффер в черновик (или возвращает удалённый)."""
    item = _find(stream, offer_id)
    if item is None:
        stream.offers.append(StreamOffer(offer_id=offer_id, status=ACTIVE))
    elif item.status == ACTIVE:
        raise StreamRuleError("Этот оффер уже есть в потоке")
    else:
        item.status = ACTIVE
    recalc_shares(stream)


def restore_offer(stream: Stream, offer_id: int) -> None:
    """Bring back: возвращает удалённый оффер из архива в поток."""
    item = _find(stream, offer_id)
    if item is None or item.status != REMOVED:
        raise StreamRuleError("Оффера нет в архиве потока")
    item.status = ACTIVE
    recalc_shares(stream)


def remove_offer(stream: Stream, offer_id: int) -> None:
    """Remove: оффер серится и получает 0%, но остаётся в архиве."""
    item = _find(stream, offer_id)
    if item is None or item.status != ACTIVE:
        raise StreamRuleError("Оффера нет в потоке")
    if not item.was_published:
        # Никогда не был в Keitaro — хранить в архиве нечего
        stream.offers.remove(item)
    else:
        item.status = REMOVED
    recalc_shares(stream)


def set_pin(
    stream: Stream, offer_id: int, pinned: bool | None, share: int | None
) -> None:
    """Пин веса. Если пришла новая доля — оффер запинивается с ней."""
    item = _find(stream, offer_id)
    if item is None or item.status != ACTIVE:
        raise StreamRuleError("Оффера нет в потоке")
    if share is not None:
        if not 0 <= share <= 100:
            raise StreamRuleError("Вес должен быть в пределах 0–100%")
        item.share = share
        item.pinned = True
    elif pinned is not None:
        item.pinned = pinned
    recalc_shares(stream)


def cancel(stream: Stream) -> None:
    """Cancel: откат черновика к опубликованному состоянию."""
    for item in list(stream.offers):
        if item.status == ACTIVE and not item.in_keitaro:
            if item.was_published:
                # Вернули из архива и передумали — обратно в архив
                item.status = REMOVED
                item.share = 0
            else:
                # Добавили до публикации — привязка удаляется
                stream.offers.remove(item)
        elif item.status == REMOVED and item.in_keitaro:
            item.status = ACTIVE
            item.share = item.published_share
        elif item.status == ACTIVE:
            item.share = item.published_share


async def push(stream: Stream, client: KeitaroClient) -> None:
    """Push to Keitaro: публикует черновик потока."""
    active = active_offers(stream)
    if active and sum(item.share for item in active) != 100:
        raise StreamRuleError("Сумма весов должна быть 100%")
    await client.update_stream_offers(
        stream.keitaro_stream_id,
        [
            {"offer_id": item.offer_id, "share": item.share, "state": "active"}
            for item in active
        ],
    )
    for item in stream.offers:
        is_active = item.status == ACTIVE
        item.in_keitaro = is_active
        item.published_share = item.share if is_active else 0
        if is_active:
            item.was_published = True


# --- Синхронизация с Keitaro -------------------------------------------


async def sync_campaign(
    db: Session, campaign: Campaign, client: KeitaroClient
) -> list[dict]:
    """Fetch streams: приводит локальную БД к состоянию Keitaro.

    * потоки без офферов добавляются как есть;
    * офферы, которых больше нет в Keitaro, уходят в архив (removed);
    * неопубликованные черновики сбрасываются, пины сохраняются.
    """
    remote_streams = await client.list_campaign_streams(campaign.keitaro_id)
    local = {item.keitaro_stream_id: item for item in campaign_streams(db, campaign)}
    remote_ids = set()

    for remote in remote_streams:
        remote_ids.add(remote["id"])
        stream = local.get(remote["id"])
        if stream is None:
            stream = Stream(campaign_id=campaign.id, keitaro_stream_id=remote["id"])
            db.add(stream)
        stream.name = remote.get("name") or f"Поток #{remote['id']}"
        stream.position = remote.get("position") or 0
        stream.schema = remote.get("schema") or ""

        remote_offers = {item["offer_id"]: item for item in remote.get("offers", [])}
        for item in list(stream.offers):
            if item.offer_id in remote_offers:
                continue
            if item.in_keitaro or (item.status == ACTIVE and item.was_published):
                # Был в Keitaro, но пропал — как будто удалили руками
                item.status = REMOVED
                item.in_keitaro = False
                item.share = 0
                item.published_share = 0
                item.pinned = False
            elif item.status == ACTIVE:
                stream.offers.remove(item)  # неопубликованный черновик

        for offer_id, remote_offer in remote_offers.items():
            item = _find(stream, offer_id)
            if item is None:
                item = StreamOffer(offer_id=offer_id)
                stream.offers.append(item)
            share = int(remote_offer.get("share") or 0)
            item.status = ACTIVE
            item.in_keitaro = True
            item.was_published = True
            item.share = item.published_share = share

    for keitaro_id, stream in local.items():
        if keitaro_id not in remote_ids:
            db.delete(stream)
    db.flush()
    db.expire_all()
    return remote_streams


def detect_geo(remote_streams: list[dict]) -> str | None:
    """Гео кампании: первая страна из фильтра country (accept) любого потока."""
    for remote in remote_streams:
        for flt in remote.get("filters") or []:
            if flt.get("name") == "country" and flt.get("mode") == "accept":
                payload = flt.get("payload") or []
                if payload:
                    return str(payload[0]).upper()[:2]
    return None


def campaign_streams(db: Session, campaign: Campaign) -> list[Stream]:
    return sorted(
        db.query(Stream).filter(Stream.campaign_id == campaign.id).all(),
        key=lambda item: (item.position, item.id),
    )


# --- Представление для API ---------------------------------------------


async def serialize_stream(stream: Stream, client: KeitaroClient) -> "StreamOut":
    """Собирает StreamOut, обогащая офферы данными справочника Keitaro."""
    from .schemas import StreamOfferOut, StreamOut

    meta = {item["id"]: item for item in await client.list_offers()}
    offers = []
    for item in stream.offers:
        info = meta.get(item.offer_id, {})
        offers.append(
            StreamOfferOut(
                offer_id=item.offer_id,
                name=info.get("name"),
                country=info.get("country"),
                payout_value=info.get("payout_value"),
                payout_currency=info.get("payout_currency"),
                status=item.status,
                share=item.share,
                pinned=item.pinned,
                in_keitaro=item.in_keitaro,
            )
        )
    return StreamOut(
        id=stream.id,
        keitaro_stream_id=stream.keitaro_stream_id,
        name=stream.name,
        position=stream.position,
        editable=is_editable(stream),
        dirty=is_dirty(stream),
        offers=offers,
    )
