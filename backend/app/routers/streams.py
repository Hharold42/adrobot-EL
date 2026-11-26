"""Редактор потока: добавить/удалить/вернуть оффер, пин веса, Push и Cancel.

Все изменения до Push — черновые и живут только в нашей БД.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import streams as logic
from ..database import get_db
from ..deps import get_keitaro
from ..keitaro import KeitaroClient, KeitaroError
from ..models import Stream
from ..schemas import OfferAdd, OfferPatch, StreamOut

router = APIRouter(prefix="/api/streams", tags=["streams"])


def _get_stream(stream_id: int, db: Session) -> Stream:
    stream = db.get(Stream, stream_id)
    if stream is None:
        raise HTTPException(status_code=404, detail="Поток не найден")
    if not logic.is_editable(stream):
        raise HTTPException(status_code=400, detail="В этом потоке нет офферов")
    return stream


async def _finish(db: Session, client: KeitaroClient, stream: Stream) -> StreamOut:
    """Фиксирует изменения и отдаёт обновлённый поток."""
    db.commit()
    db.refresh(stream)
    return await logic.serialize_stream(stream, client)


def _rule_error(db: Session, exc: logic.StreamRuleError) -> HTTPException:
    db.rollback()
    return HTTPException(status_code=400, detail=str(exc))


def _keitaro_error(db: Session, exc: KeitaroError) -> HTTPException:
    db.rollback()
    return HTTPException(status_code=502, detail=str(exc))


@router.post("/{stream_id}/offers", response_model=StreamOut)
async def add_offer(
    stream_id: int,
    payload: OfferAdd,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> StreamOut:
    """Добавляет оффер в черновик потока (удалённый — возвращает)."""
    stream = _get_stream(stream_id, db)
    try:
        await client.get_offer(payload.offer_id)
    except KeitaroError as exc:
        raise HTTPException(
            status_code=404, detail=f"Оффер {payload.offer_id} не найден в Keitaro"
        ) from exc
    try:
        logic.add_offer(stream, payload.offer_id)
        return await _finish(db, client, stream)
    except logic.StreamRuleError as exc:
        raise _rule_error(db, exc) from exc
    except KeitaroError as exc:
        raise _keitaro_error(db, exc) from exc


@router.delete("/{stream_id}/offers/{offer_id}", response_model=StreamOut)
async def remove_offer(
    stream_id: int,
    offer_id: int,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> StreamOut:
    """Remove: оффер получает 0% и уходит в архив (после Push исчезнет из Keitaro)."""
    stream = _get_stream(stream_id, db)
    try:
        logic.remove_offer(stream, offer_id)
        return await _finish(db, client, stream)
    except logic.StreamRuleError as exc:
        raise _rule_error(db, exc) from exc
    except KeitaroError as exc:
        raise _keitaro_error(db, exc) from exc


@router.post("/{stream_id}/offers/{offer_id}/restore", response_model=StreamOut)
async def restore_offer(
    stream_id: int,
    offer_id: int,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> StreamOut:
    """Bring back: возвращает оффер из архива в поток."""
    stream = _get_stream(stream_id, db)
    try:
        logic.restore_offer(stream, offer_id)
        return await _finish(db, client, stream)
    except logic.StreamRuleError as exc:
        raise _rule_error(db, exc) from exc
    except KeitaroError as exc:
        raise _keitaro_error(db, exc) from exc


@router.patch("/{stream_id}/offers/{offer_id}", response_model=StreamOut)
async def patch_offer(
    stream_id: int,
    offer_id: int,
    payload: OfferPatch,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> StreamOut:
    """Пин веса: остальные офферы перераспределяются, запиненные остаются."""
    stream = _get_stream(stream_id, db)
    try:
        logic.set_pin(stream, offer_id, payload.pinned, payload.share)
        return await _finish(db, client, stream)
    except logic.StreamRuleError as exc:
        raise _rule_error(db, exc) from exc
    except KeitaroError as exc:
        raise _keitaro_error(db, exc) from exc


@router.post("/{stream_id}/push", response_model=StreamOut)
async def push_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> StreamOut:
    """Push to Keitaro: публикует черновик потока."""
    stream = _get_stream(stream_id, db)
    try:
        await logic.push(stream, client)
        return await _finish(db, client, stream)
    except logic.StreamRuleError as exc:
        raise _rule_error(db, exc) from exc
    except KeitaroError as exc:
        raise _keitaro_error(db, exc) from exc


@router.post("/{stream_id}/cancel", response_model=StreamOut)
async def cancel_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> StreamOut:
    """Cancel: откатывает неопубликованные изменения потока."""
    stream = _get_stream(stream_id, db)
    try:
        logic.cancel(stream)
        return await _finish(db, client, stream)
    except KeitaroError as exc:
        raise _keitaro_error(db, exc) from exc
