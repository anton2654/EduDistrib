from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.base import Base


class TeacherSlot(Base):
    __tablename__ = "teacher_slots"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_teacher_slots_time_range"),
        CheckConstraint("capacity > 0", name="ck_teacher_slots_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
    )
    discipline_id: Mapped[int] = mapped_column(
        ForeignKey("disciplines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    teacher: Mapped["Teacher"] = relationship(back_populates="slots")
    discipline: Mapped["Discipline"] = relationship(back_populates="slots")
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="slot",
        cascade="all, delete-orphan",
    )
