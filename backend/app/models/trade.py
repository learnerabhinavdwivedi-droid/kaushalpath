"""Trade catalog and aliases (Phase 19 Data Foundation)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EvidenceMixin, SourceMixin, TimestampMixin


class Trade(Base, TimestampMixin, SourceMixin, EvidenceMixin):
    __tablename__ = "trades"

    trade_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    name_hi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nco_code: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    nsqf_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qp_code: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    ncvt_trade_code: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    aliases: Mapped[list[TradeAlias]] = relationship(
        "TradeAlias", back_populates="trade", cascade="all, delete-orphan"
    )


class TradeAlias(Base, TimestampMixin):
    __tablename__ = "trade_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("trades.trade_id", ondelete="CASCADE"), index=True, nullable=False
    )
    alias: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)

    trade: Mapped[Trade] = relationship("Trade", back_populates="aliases")
