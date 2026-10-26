from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500))
    adapter: Mapped[str] = mapped_column(String(50))
    enabled: Mapped[bool] = mapped_column(default=True)


class Notice(Base):
    __tablename__ = "notices"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    body_text: Mapped[str] = mapped_column(Text, default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    criteria: Mapped[dict | None] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="notice")


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"))
    file_url: Mapped[str] = mapped_column(String(1000))
    kind: Mapped[str] = mapped_column(String(10))  # hwp|pdf|image|other
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    notice: Mapped[Notice] = relationship(back_populates="attachments")


class Device(Base):
    """개인정보 없음: 푸시 토큰 + 익명 조건 태그만."""

    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    push_token: Mapped[str] = mapped_column(String(200), unique=True)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (UniqueConstraint("device_id", "notice_id", "kind", "content_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"))
    kind: Mapped[str] = mapped_column(String(20))  # new|changed|d3
    content_hash: Mapped[str] = mapped_column(String(64))
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
