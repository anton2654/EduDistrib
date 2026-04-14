from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.application.dto.enrollment_dto import (
    CityCreateDTO,
    DisciplineCreateDTO,
    StudentCreateDTO,
    TeacherSlotUpdateDTO,
    TeacherCreateDTO,
    TeacherSlotCreateDTO,
)
from app.domain.entities.booking import Booking
from app.domain.entities.city import City
from app.domain.entities.discipline import Discipline
from app.domain.entities.student import Student
from app.domain.entities.teacher import Teacher
from app.domain.entities.teacher_slot import TeacherSlot


@dataclass(frozen=True)
class AvailableSlotProjection:
    slot_id: int
    teacher_id: int
    teacher_name: str
    city_id: int
    city_name: str
    discipline_id: int
    discipline_name: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    reserved_seats: int


@dataclass(frozen=True)
class BookingProjection:
    booking_id: int
    student_id: int
    student_name: str
    student_email: str
    slot_id: int
    teacher_id: int
    teacher_name: str
    city_id: int
    city_name: str
    discipline_id: int
    discipline_name: str
    starts_at: datetime
    ends_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class TeacherSlotProjection:
    slot_id: int
    teacher_id: int
    discipline_id: int
    discipline_name: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    reserved_seats: int
    is_active: bool
    created_at: datetime


class EnrollmentRepositoryInterface(ABC):
    @abstractmethod
    async def create_city(self, city_in: CityCreateDTO) -> City:
        raise NotImplementedError

    @abstractmethod
    async def list_cities(self) -> list[City]:
        raise NotImplementedError

    @abstractmethod
    async def get_city_by_id(self, city_id: int) -> City | None:
        raise NotImplementedError

    @abstractmethod
    async def create_discipline(self, discipline_in: DisciplineCreateDTO) -> Discipline:
        raise NotImplementedError

    @abstractmethod
    async def list_disciplines(self) -> list[Discipline]:
        raise NotImplementedError

    @abstractmethod
    async def get_discipline_by_id(self, discipline_id: int) -> Discipline | None:
        raise NotImplementedError

    @abstractmethod
    async def create_teacher(self, teacher_in: TeacherCreateDTO) -> Teacher:
        raise NotImplementedError

    @abstractmethod
    async def list_teachers(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
    ) -> list[Teacher]:
        raise NotImplementedError

    @abstractmethod
    async def get_teacher_by_id(self, teacher_id: int) -> Teacher | None:
        raise NotImplementedError

    @abstractmethod
    async def teacher_has_discipline(self, teacher_id: int, discipline_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def create_student(self, student_in: StudentCreateDTO) -> Student:
        raise NotImplementedError

    @abstractmethod
    async def list_students(
        self,
        city_id: int | None = None,
        email: str | None = None,
    ) -> list[Student]:
        raise NotImplementedError

    @abstractmethod
    async def get_student_by_id(self, student_id: int) -> Student | None:
        raise NotImplementedError

    @abstractmethod
    async def create_slot(self, slot_in: TeacherSlotCreateDTO) -> TeacherSlot:
        raise NotImplementedError

    @abstractmethod
    async def get_slot_by_id(self, slot_id: int) -> TeacherSlot | None:
        raise NotImplementedError

    @abstractmethod
    async def list_teacher_slots(self, teacher_id: int) -> list[TeacherSlotProjection]:
        raise NotImplementedError

    @abstractmethod
    async def update_slot(self, slot: TeacherSlot, slot_in: TeacherSlotUpdateDTO) -> TeacherSlot:
        raise NotImplementedError

    @abstractmethod
    async def delete_slot(self, slot: TeacherSlot) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_available_slots(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
    ) -> list[AvailableSlotProjection]:
        raise NotImplementedError

    @abstractmethod
    async def count_slot_bookings(self, slot_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    async def has_booking(self, student_id: int, slot_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def create_booking(self, student_id: int, slot_id: int) -> Booking:
        raise NotImplementedError

    @abstractmethod
    async def list_bookings(self, student_id: int | None = None) -> list[BookingProjection]:
        raise NotImplementedError

    @abstractmethod
    async def get_booking_by_id(self, booking_id: int) -> Booking | None:
        raise NotImplementedError

    @abstractmethod
    async def delete_booking(self, booking: Booking) -> None:
        raise NotImplementedError
