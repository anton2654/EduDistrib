from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.base import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("student_id", "slot_id", name="uq_bookings_student_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_id: Mapped[int] = mapped_column(
        ForeignKey("teacher_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    student: Mapped["Student"] = relationship(back_populates="bookings")
    slot: Mapped["TeacherSlot"] = relationship(back_populates="bookings")
