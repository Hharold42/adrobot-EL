"""Pydantic-схемы запросов и ответов API."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class CampaignCreate(BaseModel):
    """Данные для создания кампании (часть 1 ТЗ)."""

    name: str = Field(min_length=1, max_length=200)
    geo_code: str = Field(min_length=2, max_length=2)
    offer_ids: list[int] = Field(min_length=1, max_length=50)

    @model_validator(mode="before")
    @classmethod
    def legacy_offer_id(cls, data):
        """Совместимость с ТЗ: одиночный offer_id превращаем в offer_ids."""
        if isinstance(data, dict) and "offer_ids" not in data and "offer_id" in data:
            data = {**data, "offer_ids": [data["offer_id"]]}
        return data

    @field_validator("offer_ids")
    @classmethod
    def offer_ids_valid(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value):
            raise ValueError("ID оффера должен быть положительным числом")
        if len(set(value)) != len(value):
            raise ValueError("Офферы в списке не должны повторяться")
        return value

    @field_validator("geo_code")
    @classmethod
    def geo_code_upper(cls, value: str) -> str:
        value = value.strip().upper()
        if not value.isalpha():
            raise ValueError("Гео-код страны должен состоять из двух букв, например DE")
        return value

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Название кампании не должно быть пустым")
        return value


class CampaignOut(BaseModel):
    """Кампания из локальной БД."""

    id: int
    keitaro_id: int
    name: str
    geo_code: str | None = None
    geo_stream_id: int | None = None
    offer_stream_id: int | None = None
    imported: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class StreamOfferOut(BaseModel):
    """Оффер в потоке: черновое состояние + данные из справочника Keitaro."""

    offer_id: int
    name: str | None = None
    country: list[str] | None = None
    payout_value: float | None = None
    payout_currency: str | None = None
    status: str  # active | removed
    share: int
    pinned: bool
    in_keitaro: bool


class StreamOut(BaseModel):
    """Поток кампании. dirty=True — есть неопубликованные изменения."""

    id: int
    keitaro_stream_id: int
    name: str
    position: int
    editable: bool
    dirty: bool
    offers: list[StreamOfferOut]


class CampaignDetail(CampaignOut):
    """Кампания + потоки для редактора."""

    streams: list[StreamOut]


class OfferAdd(BaseModel):
    offer_id: int = Field(gt=0)


class OfferPatch(BaseModel):
    """Пин веса: pinned переключает пин, share запинивает оффер с новым весом."""

    pinned: bool | None = None
    share: int | None = Field(default=None, ge=0, le=100)


class OfferOut(BaseModel):
    """Оффер из справочника Keitaro."""

    id: int
    name: str
    country: list[str]
    payout_value: float
    payout_currency: str
    state: str


class CountryOut(BaseModel):
    """Гео, собранное из офферов: код страны + сколько под него офферов."""

    code: str
    offers_count: int
    region: str


class KeitaroCampaignOut(BaseModel):
    """Кампания из Keitaro для диалога импорта."""

    id: int
    name: str
    state: str
    imported: bool


class CampaignImport(BaseModel):
    keitaro_ids: list[int] = Field(min_length=1, max_length=200)
