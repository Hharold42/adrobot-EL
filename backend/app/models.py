"""ORM-модели локальной БД."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Campaign(Base):
    """Кампания, созданная через наш сервис.

    Храним связь с Keitaro: id кампании и id потоков. Кампании, созданные
    в самом Keitaro, попадают сюда через импорт (imported=True).
    """

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    # У импортированных из Keitaro кампаний гео и «наши» потоки могут быть неизвестны
    geo_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    geo_stream_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offer_stream_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imported: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Stream(Base):
    """Поток кампании, подтянутый из Keitaro (Fetch streams).

    Потоки без офферов хранятся «как есть»: только название и позиция,
    содержимое редиректа и фильтры нас не интересуют.
    """

    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    keitaro_stream_id: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    # schema потока в Keitaro: landings — поток с офферами, redirect — простой редирект
    schema: Mapped[str] = mapped_column(String(50), default="")

    offers: Mapped[list["StreamOffer"]] = relationship(
        back_populates="stream",
        cascade="all, delete-orphan",
        order_by="StreamOffer.id",
    )


class StreamOffer(Base):
    """Привязка оффера к потоку + его «черновое» состояние.

    share/status — то, что видит пользователь в обёртке (черновик),
    in_keitaro/published_share — то, что реально лежит в Keitaro.
    Поток «грязный» (жёлтый), пока эти состояния расходятся.
    """

    __tablename__ = "stream_offers"
    __table_args__ = (UniqueConstraint("stream_id", "offer_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(
        ForeignKey("streams.id", ondelete="CASCADE"), index=True
    )
    offer_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="active")  # active | removed
    share: Mapped[int] = mapped_column(Integer, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    in_keitaro: Mapped[bool] = mapped_column(Boolean, default=False)
    was_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_share: Mapped[int] = mapped_column(Integer, default=0)

    stream: Mapped[Stream] = relationship(back_populates="offers")
