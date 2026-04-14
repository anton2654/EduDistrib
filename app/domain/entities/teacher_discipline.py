from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.base import Base


class TeacherDiscipline(Base):
    __tablename__ = "teacher_disciplines"

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    discipline_id: Mapped[int] = mapped_column(
        ForeignKey("disciplines.id", ondelete="CASCADE"),
        primary_key=True,
    )

    teacher: Mapped["Teacher"] = relationship(back_populates="discipline_links")
    discipline: Mapped["Discipline"] = relationship(back_populates="teacher_links")
