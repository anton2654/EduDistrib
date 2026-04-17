from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False)

    city: Mapped["City"] = relationship(back_populates="teachers")
    discipline_links: Mapped[list["TeacherDiscipline"]] = relationship(
        back_populates="teacher",
        cascade="all, delete-orphan",
    )
    slots: Mapped[list["TeacherSlot"]] = relationship(
        back_populates="teacher",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="teacher",
        cascade="all, delete-orphan",
    )
    account: Mapped["UserAccount | None"] = relationship(back_populates="teacher")
