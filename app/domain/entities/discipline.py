from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.base import Base


class Discipline(Base):
    __tablename__ = "disciplines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

    teacher_links: Mapped[list["TeacherDiscipline"]] = relationship(
        back_populates="discipline",
        cascade="all, delete-orphan",
    )
    slots: Mapped[list["TeacherSlot"]] = relationship(back_populates="discipline")
