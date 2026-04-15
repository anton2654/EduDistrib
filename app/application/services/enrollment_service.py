from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.application.dto.enrollment_dto import (
    BookingCreateDTO,
    CityCreateDTO,
    DisciplineCreateDTO,
    StudentCreateDTO,
    TeacherSlotManageCreateDTO,
    TeacherSlotUpdateDTO,
    TeacherCreateDTO,
    TeacherSlotCreateDTO,
)
from app.application.interfaces.enrollment_repository import (
    AnalyticsOverviewProjection,
    AvailableSlotProjection,
    BookingProjection,
    DisciplineAnalyticsProjection,
    EnrollmentRepositoryInterface,
    TeacherAnalyticsProjection,
    TeacherSlotProjection,
)
from app.domain.entities.booking import Booking
from app.domain.entities.city import City
from app.domain.entities.discipline import Discipline
from app.domain.entities.student import Student
from app.domain.entities.teacher import Teacher
from app.domain.entities.teacher_slot import TeacherSlot


class EnrollmentError(Exception):
    pass


class CityNotFoundError(EnrollmentError):
    def __init__(self, city_id: int) -> None:
        super().__init__(f"City with id {city_id} was not found.")


class DisciplineNotFoundError(EnrollmentError):
    def __init__(self, discipline_id: int) -> None:
        super().__init__(f"Discipline with id {discipline_id} was not found.")


class TeacherNotFoundError(EnrollmentError):
    def __init__(self, teacher_id: int) -> None:
        super().__init__(f"Teacher with id {teacher_id} was not found.")


class StudentNotFoundError(EnrollmentError):
    def __init__(self, student_id: int) -> None:
        super().__init__(f"Student with id {student_id} was not found.")


class SlotNotFoundError(EnrollmentError):
    def __init__(self, slot_id: int) -> None:
        super().__init__(f"Slot with id {slot_id} was not found.")


class TeacherDisciplineMismatchError(EnrollmentError):
    def __init__(self, teacher_id: int, discipline_id: int) -> None:
        super().__init__(
            f"Teacher {teacher_id} is not assigned to discipline {discipline_id}.",
        )


class SlotIsInactiveError(EnrollmentError):
    def __init__(self, slot_id: int) -> None:
        super().__init__(f"Slot {slot_id} is inactive.")


class SlotFullError(EnrollmentError):
    def __init__(self, slot_id: int) -> None:
        super().__init__(f"Slot {slot_id} has no available seats.")


class DuplicateBookingError(EnrollmentError):
    def __init__(self, student_id: int, slot_id: int) -> None:
        super().__init__(f"Student {student_id} is already booked for slot {slot_id}.")


class BookingNotFoundError(EnrollmentError):
    def __init__(self, booking_id: int) -> None:
        super().__init__(f"Booking with id {booking_id} was not found.")


class BookingOwnershipError(EnrollmentError):
    def __init__(self, booking_id: int) -> None:
        super().__init__(f"Booking {booking_id} does not belong to the current student.")


class TeacherSlotAccessError(EnrollmentError):
    def __init__(self, slot_id: int) -> None:
        super().__init__(f"Slot {slot_id} does not belong to the current teacher.")


class SlotTimeRangeError(EnrollmentError):
    def __init__(self) -> None:
        super().__init__("Slot ends_at must be later than starts_at.")


class AnalyticsFilterRangeError(EnrollmentError):
    def __init__(self) -> None:
        super().__init__("Analytics filter ends_to must be later than starts_from.")


class EnrollmentService:
    def __init__(self, repository: EnrollmentRepositoryInterface) -> None:
        self._repository = repository

    async def create_city(self, city_in: CityCreateDTO) -> City:
        return await self._repository.create_city(city_in)

    async def list_cities(self) -> list[City]:
        return await self._repository.list_cities()

    async def create_discipline(self, discipline_in: DisciplineCreateDTO) -> Discipline:
        return await self._repository.create_discipline(discipline_in)

    async def list_disciplines(self) -> list[Discipline]:
        return await self._repository.list_disciplines()

    async def create_teacher(self, teacher_in: TeacherCreateDTO) -> Teacher:
        city = await self._repository.get_city_by_id(teacher_in.city_id)
        if city is None:
            raise CityNotFoundError(teacher_in.city_id)

        unique_discipline_ids = list(dict.fromkeys(teacher_in.discipline_ids))
        for discipline_id in unique_discipline_ids:
            discipline = await self._repository.get_discipline_by_id(discipline_id)
            if discipline is None:
                raise DisciplineNotFoundError(discipline_id)

        teacher_payload = TeacherCreateDTO(
            full_name=teacher_in.full_name,
            city_id=teacher_in.city_id,
            discipline_ids=unique_discipline_ids,
        )
        created_teacher = await self._repository.create_teacher(teacher_payload)
        teacher_with_links = await self._repository.get_teacher_by_id(created_teacher.id)
        return teacher_with_links or created_teacher

    async def list_teachers(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
    ) -> list[Teacher]:
        if city_id is not None:
            city = await self._repository.get_city_by_id(city_id)
            if city is None:
                raise CityNotFoundError(city_id)

        if discipline_id is not None:
            discipline = await self._repository.get_discipline_by_id(discipline_id)
            if discipline is None:
                raise DisciplineNotFoundError(discipline_id)

        return await self._repository.list_teachers(city_id=city_id, discipline_id=discipline_id)

    async def create_student(self, student_in: StudentCreateDTO) -> Student:
        city = await self._repository.get_city_by_id(student_in.city_id)
        if city is None:
            raise CityNotFoundError(student_in.city_id)

        return await self._repository.create_student(student_in)

    async def list_students(
        self,
        city_id: int | None = None,
        email: str | None = None,
    ) -> list[Student]:
        if city_id is not None:
            city = await self._repository.get_city_by_id(city_id)
            if city is None:
                raise CityNotFoundError(city_id)

        normalized_email = email.strip().lower() if email is not None else None
        return await self._repository.list_students(city_id=city_id, email=normalized_email)

    async def create_slot(self, slot_in: TeacherSlotCreateDTO) -> TeacherSlot:
        teacher = await self._repository.get_teacher_by_id(slot_in.teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(slot_in.teacher_id)

        discipline = await self._repository.get_discipline_by_id(slot_in.discipline_id)
        if discipline is None:
            raise DisciplineNotFoundError(slot_in.discipline_id)

        teacher_has_discipline = await self._repository.teacher_has_discipline(
            slot_in.teacher_id,
            slot_in.discipline_id,
        )
        if not teacher_has_discipline:
            raise TeacherDisciplineMismatchError(slot_in.teacher_id, slot_in.discipline_id)

        return await self._repository.create_slot(slot_in)

    async def create_slot_for_teacher(
        self,
        teacher_id: int,
        slot_in: TeacherSlotManageCreateDTO,
    ) -> TeacherSlot:
        teacher = await self._repository.get_teacher_by_id(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)

        discipline = await self._repository.get_discipline_by_id(slot_in.discipline_id)
        if discipline is None:
            raise DisciplineNotFoundError(slot_in.discipline_id)

        has_discipline = await self._repository.teacher_has_discipline(
            teacher_id,
            slot_in.discipline_id,
        )
        if not has_discipline:
            raise TeacherDisciplineMismatchError(teacher_id, slot_in.discipline_id)

        create_dto = TeacherSlotCreateDTO(
            teacher_id=teacher_id,
            discipline_id=slot_in.discipline_id,
            starts_at=slot_in.starts_at,
            ends_at=slot_in.ends_at,
            capacity=slot_in.capacity,
            is_active=slot_in.is_active,
        )
        return await self._repository.create_slot(create_dto)

    async def list_teacher_slots(self, teacher_id: int) -> list[TeacherSlotProjection]:
        teacher = await self._repository.get_teacher_by_id(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)

        return await self._repository.list_teacher_slots(teacher_id)

    async def update_slot_for_teacher(
        self,
        teacher_id: int,
        slot_id: int,
        slot_in: TeacherSlotUpdateDTO,
    ) -> TeacherSlot:
        slot = await self._repository.get_slot_by_id(slot_id)
        if slot is None:
            raise SlotNotFoundError(slot_id)

        if slot.teacher_id != teacher_id:
            raise TeacherSlotAccessError(slot_id)

        if slot_in.discipline_id is not None:
            discipline = await self._repository.get_discipline_by_id(slot_in.discipline_id)
            if discipline is None:
                raise DisciplineNotFoundError(slot_in.discipline_id)

            has_discipline = await self._repository.teacher_has_discipline(
                teacher_id,
                slot_in.discipline_id,
            )
            if not has_discipline:
                raise TeacherDisciplineMismatchError(teacher_id, slot_in.discipline_id)

        new_starts_at = slot_in.starts_at if slot_in.starts_at is not None else slot.starts_at
        new_ends_at = slot_in.ends_at if slot_in.ends_at is not None else slot.ends_at
        if new_ends_at <= new_starts_at:
            raise SlotTimeRangeError

        return await self._repository.update_slot(slot, slot_in)

    async def delete_slot_for_teacher(self, teacher_id: int, slot_id: int) -> None:
        slot = await self._repository.get_slot_by_id(slot_id)
        if slot is None:
            raise SlotNotFoundError(slot_id)

        if slot.teacher_id != teacher_id:
            raise TeacherSlotAccessError(slot_id)

        await self._repository.delete_slot(slot)

    async def list_available_slots(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
    ) -> list[AvailableSlotProjection]:
        if city_id is not None:
            city = await self._repository.get_city_by_id(city_id)
            if city is None:
                raise CityNotFoundError(city_id)

        if discipline_id is not None:
            discipline = await self._repository.get_discipline_by_id(discipline_id)
            if discipline is None:
                raise DisciplineNotFoundError(discipline_id)

        if teacher_id is not None:
            teacher = await self._repository.get_teacher_by_id(teacher_id)
            if teacher is None:
                raise TeacherNotFoundError(teacher_id)

        return await self._repository.list_available_slots(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
        )

    async def get_overview_analytics(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
        starts_from: datetime | None = None,
        ends_to: datetime | None = None,
    ) -> AnalyticsOverviewProjection:
        await self._validate_analytics_filters(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )
        return await self._repository.get_overview_analytics(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )

    async def list_teacher_analytics(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
        starts_from: datetime | None = None,
        ends_to: datetime | None = None,
    ) -> list[TeacherAnalyticsProjection]:
        await self._validate_analytics_filters(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )
        return await self._repository.list_teacher_analytics(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )

    async def list_discipline_analytics(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
        starts_from: datetime | None = None,
        ends_to: datetime | None = None,
    ) -> list[DisciplineAnalyticsProjection]:
        await self._validate_analytics_filters(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )
        return await self._repository.list_discipline_analytics(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )

    async def create_booking(self, booking_in: BookingCreateDTO) -> Booking:
        student = await self._repository.get_student_by_id(booking_in.student_id)
        if student is None:
            raise StudentNotFoundError(booking_in.student_id)

        slot = await self._repository.get_slot_by_id(booking_in.slot_id)
        if slot is None:
            raise SlotNotFoundError(booking_in.slot_id)

        if not slot.is_active:
            raise SlotIsInactiveError(slot.id)

        existing_booking = await self._repository.has_booking(booking_in.student_id, booking_in.slot_id)
        if existing_booking:
            raise DuplicateBookingError(booking_in.student_id, booking_in.slot_id)

        booked_seats = await self._repository.count_slot_bookings(booking_in.slot_id)
        if booked_seats >= slot.capacity:
            raise SlotFullError(slot.id)

        try:
            return await self._repository.create_booking(
                booking_in.student_id,
                booking_in.slot_id,
            )
        except IntegrityError as error:
            raise DuplicateBookingError(booking_in.student_id, booking_in.slot_id) from error

    async def list_bookings(self, student_id: int | None = None) -> list[BookingProjection]:
        if student_id is not None:
            student = await self._repository.get_student_by_id(student_id)
            if student is None:
                raise StudentNotFoundError(student_id)

        return await self._repository.list_bookings(student_id=student_id)

    async def cancel_booking(
        self,
        booking_id: int,
        student_id: int | None = None,
    ) -> None:
        booking = await self._repository.get_booking_by_id(booking_id)
        if booking is None:
            raise BookingNotFoundError(booking_id)

        if student_id is not None and booking.student_id != student_id:
            raise BookingOwnershipError(booking_id)

        await self._repository.delete_booking(booking)

    async def _validate_analytics_filters(
        self,
        *,
        city_id: int | None,
        discipline_id: int | None,
        teacher_id: int | None,
        starts_from: datetime | None,
        ends_to: datetime | None,
    ) -> None:
        if city_id is not None:
            city = await self._repository.get_city_by_id(city_id)
            if city is None:
                raise CityNotFoundError(city_id)

        if discipline_id is not None:
            discipline = await self._repository.get_discipline_by_id(discipline_id)
            if discipline is None:
                raise DisciplineNotFoundError(discipline_id)

        if teacher_id is not None:
            teacher = await self._repository.get_teacher_by_id(teacher_id)
            if teacher is None:
                raise TeacherNotFoundError(teacher_id)

        if starts_from is not None and ends_to is not None and ends_to <= starts_from:
            raise AnalyticsFilterRangeError
