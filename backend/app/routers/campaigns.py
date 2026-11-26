"""Эндпоинты кампаний: создание (часть 1 ТЗ) и просмотр с потоками (часть 2)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_keitaro
from ..keitaro import KeitaroClient, KeitaroError
from ..models import Campaign
from ..schemas import (
    CampaignCreate,
    CampaignDetail,
    CampaignImport,
    CampaignOut,
    KeitaroCampaignOut,
)
from ..streams import (
    campaign_streams,
    detect_geo,
    serialize_stream,
    sync_campaign,
)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _keitaro_guard(exc: KeitaroError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


def _get_local_campaign(campaign_id: int, db: Session) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    return campaign


async def build_detail(
    record: Campaign, db: Session, client: KeitaroClient
) -> CampaignDetail:
    streams = [
        await serialize_stream(stream, client) for stream in campaign_streams(db, record)
    ]
    return CampaignDetail(
        **CampaignOut.model_validate(record).model_dump(), streams=streams
    )


@router.post("", response_model=CampaignDetail, status_code=201)
async def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> CampaignDetail:
    """Создаватор кампаний: кампания + гео-поток на Google + поток на офферы."""
    for offer_id in payload.offer_ids:
        try:
            await client.get_offer(offer_id)
        except KeitaroError as exc:
            raise HTTPException(
                status_code=404, detail=f"Оффер {offer_id} не найден в Keitaro"
            ) from exc

    settings = get_settings()
    full_name = f"{settings.campaign_name_prefix}{payload.name}"

    try:
        defaults = await client.resolve_defaults()
        campaign = await client.create_campaign(
            name=full_name,
            group_id=defaults["group_id"],
            domain_id=defaults["domain_id"],
            traffic_source_id=defaults["traffic_source_id"],
        )
    except KeitaroError as exc:
        raise _keitaro_guard(exc) from exc

    keitaro_id = campaign["id"]
    try:
        geo_stream = await client.create_geo_stream(
            keitaro_id, payload.geo_code, settings.geo_redirect_url
        )
        offer_stream = await client.create_offer_stream(keitaro_id, payload.offer_ids)
    except KeitaroError as exc:
        # Компенсация: не оставляем в Keitaro полупустую кампанию
        try:
            await client.delete_campaign(keitaro_id)
        except KeitaroError:
            pass
        raise _keitaro_guard(exc) from exc

    record = Campaign(
        keitaro_id=keitaro_id,
        name=full_name,
        geo_code=payload.geo_code,
        geo_stream_id=geo_stream["id"],
        offer_stream_id=offer_stream["id"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        await sync_campaign(db, record, client)
        db.commit()
    except KeitaroError as exc:
        db.rollback()
        raise _keitaro_guard(exc) from exc
    return await build_detail(record, db, client)


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)) -> list[Campaign]:
    """Список кампаний, созданных через сервис."""
    return list(db.scalars(select(Campaign).order_by(Campaign.created_at.desc())))


@router.get("/keitaro", response_model=list[KeitaroCampaignOut])
async def list_keitaro_campaigns(
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> list[KeitaroCampaignOut]:
    """Кампании из Keitaro (для импорта) с отметкой, какие уже у нас."""
    try:
        remote = await client.list_campaigns()
    except KeitaroError as exc:
        raise _keitaro_guard(exc) from exc
    known = set(db.scalars(select(Campaign.keitaro_id)))
    return [
        KeitaroCampaignOut(
            id=item["id"],
            name=item["name"],
            state=item.get("state", ""),
            imported=item["id"] in known,
        )
        for item in sorted(remote, key=lambda c: c["id"], reverse=True)
    ]


@router.post("/import", response_model=list[CampaignOut])
async def import_campaigns(
    payload: CampaignImport,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> list[Campaign]:
    """Бэкфилл: импортирует кампании, созданные в самом Keitaro, вместе с потоками."""
    known = set(db.scalars(select(Campaign.keitaro_id)))
    imported: list[Campaign] = []
    try:
        for keitaro_id in dict.fromkeys(payload.keitaro_ids):
            if keitaro_id in known:
                continue
            try:
                remote = await client.get_campaign(keitaro_id)
            except KeitaroError as exc:
                raise HTTPException(
                    status_code=404, detail=f"Кампания {keitaro_id} не найдена в Keitaro"
                ) from exc
            record = Campaign(keitaro_id=keitaro_id, name=remote["name"], imported=True)
            db.add(record)
            db.flush()
            streams = await sync_campaign(db, record, client)
            record.geo_code = detect_geo(streams)
            imported.append(record)
        db.commit()
    except KeitaroError as exc:
        db.rollback()
        raise _keitaro_guard(exc) from exc
    except HTTPException:
        db.rollback()
        raise
    return imported


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> CampaignDetail:
    """Кампания + потоки из локальной БД (при первом открытии — Fetch из Keitaro)."""
    record = _get_local_campaign(campaign_id, db)
    try:
        if not campaign_streams(db, record):
            await sync_campaign(db, record, client)
            db.commit()
        return await build_detail(record, db, client)
    except KeitaroError as exc:
        db.rollback()
        raise _keitaro_guard(exc) from exc


@router.post("/{campaign_id}/fetch", response_model=CampaignDetail)
async def fetch_streams(
    campaign_id: int,
    db: Session = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> CampaignDetail:
    """Fetch streams: подтягивает потоки из Keitaro, неопубликованные правки сбрасываются."""
    record = _get_local_campaign(campaign_id, db)
    try:
        await sync_campaign(db, record, client)
        db.commit()
        return await build_detail(record, db, client)
    except KeitaroError as exc:
        db.rollback()
        raise _keitaro_guard(exc) from exc
