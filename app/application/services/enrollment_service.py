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
    ReviewProjection,
    TeacherRatingSummary,
    TeacherSlotBookingProjection,
    TeacherAnalyticsProjection,
    TeacherSlotProjection,
)
from app.domain.entities.booking import Booking, BookingStatus
from app.domain.entities.city import City
from app.domain.entities.discipline import Discipline
from app.domain.entities.review import Review
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


class BookingSlotMismatchError(EnrollmentError):
    def __init__(self, booking_id: int, slot_id: int) -> None:
        super().__init__(f"Booking {booking_id} does not belong to slot {slot_id}.")


class TeacherSlotAccessError(EnrollmentError):
    def __init__(self, slot_id: int) -> None:
        super().__init__(f"Slot {slot_id} does not belong to the current teacher.")


class SlotTimeRangeError(EnrollmentError):
    def __init__(self) -> None:
        super().__init__("Slot ends_at must be later than starts_at.")


class SlotCapacityBelowReservedError(EnrollmentError):
    def __init__(self, slot_id: int, reserved_seats: int, requested_capacity: int) -> None:
        super().__init__(
            f"Slot {slot_id} has {reserved_seats} active bookings, capacity {requested_capacity} is too small.",
        )


class SlotUpdateLockedByActiveBookingsError(EnrollmentError):
    def __init__(self, slot_id: int, field: str) -> None:
        super().__init__(
            f"Slot {slot_id} has active bookings, updating {field} is not allowed.",
        )


class BookingStatusTransitionError(EnrollmentError):
    def __init__(self, booking_id: int, from_status: BookingStatus, to_status: BookingStatus) -> None:
        super().__init__(
            f"Booking {booking_id} cannot be moved from {from_status.value} to {to_status.value}.",
        )


class StudentTimeConflictError(EnrollmentError):
    def __init__(self) -> None:
        super().__init__("Student already has another active booking in this time range.")


class ReviewNotAllowedError(EnrollmentError):
    def __init__(self) -> None:
        super().__init__("Review can be left only for your own completed booking.")


class ReviewAlreadyExistsError(EnrollmentError):
    def __init__(self, booking_id: int) -> None:
        super().__init__(
            f"Review for booking {booking_id} already exists.",
        )


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

        created_teacher = await self._repository.create_teacher(teacher_in)
        teacher_with_links = await self._repository.get_teacher_by_id(created_teacher.id)
        return teacher_with_links or created_teacher

    async def list_teachers(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        search_query: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Teacher]:
        if city_id is not None:
            city = await self._repository.get_city_by_id(city_id)
            if city is None:
                raise CityNotFoundError(city_id)

        if discipline_id is not None:
            discipline = await self._repository.get_discipline_by_id(discipline_id)
            if discipline is None:
                raise DisciplineNotFoundError(discipline_id)

        normalized_search_query = (
            search_query.strip() if search_query is not None else None
        )
        if normalized_search_query == "":
            normalized_search_query = None

        return await self._repository.list_teachers(
            city_id=city_id,
            discipline_id=discipline_id,
            search_query=normalized_search_query,
            skip=skip,
            limit=limit,
        )

    async def get_teacher_rating_summaries(
        self,
        teacher_ids: list[int],
    ) -> dict[int, TeacherRatingSummary]:
        return await self._repository.get_teacher_rating_summaries(teacher_ids)

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

        create_dto = TeacherSlotCreateDTO(
            teacher_id=teacher_id,
            discipline_id=slot_in.discipline_id,
            starts_at=slot_in.starts_at,
            ends_at=slot_in.ends_at,
            description=slot_in.description,
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

        active_bookings = await self._repository.count_slot_bookings(slot_id)

        if slot_in.capacity is not None and slot_in.capacity < active_bookings:
            raise SlotCapacityBelowReservedError(
                slot_id=slot_id,
                reserved_seats=active_bookings,
                requested_capacity=slot_in.capacity,
            )

        if active_bookings > 0:
            starts_changed = slot_in.starts_at is not None and slot_in.starts_at != slot.starts_at
            ends_changed = slot_in.ends_at is not None and slot_in.ends_at != slot.ends_at
            discipline_changed = (
                slot_in.discipline_id is not None and slot_in.discipline_id != slot.discipline_id
            )

            if starts_changed or ends_changed:
                raise SlotUpdateLockedByActiveBookingsError(slot_id, "time range")

            if discipline_changed:
                raise SlotUpdateLockedByActiveBookingsError(slot_id, "discipline")

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
        skip: int = 0,
        limit: int = 50,
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
            skip=skip,
            limit=limit,
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

        existing_booking = await self._repository.has_active_booking(booking_in.student_id, booking_in.slot_id)
        if existing_booking:
            raise DuplicateBookingError(booking_in.student_id, booking_in.slot_id)

        has_time_conflict = await self._repository.student_has_time_conflict(
            booking_in.student_id,
            slot.starts_at,
            slot.ends_at,
        )
        if has_time_conflict:
            raise StudentTimeConflictError

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

    async def list_bookings(
        self,
        student_id: int | None = None,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[BookingProjection]:
        if student_id is not None:
            student = await self._repository.get_student_by_id(student_id)
            if student is None:
                raise StudentNotFoundError(student_id)

        return await self._repository.list_bookings(
            student_id=student_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    async def list_teacher_slot_bookings(
        self,
        teacher_id: int,
        slot_id: int,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TeacherSlotBookingProjection]:
        slot = await self._repository.get_slot_by_id(slot_id)
        if slot is None:
            raise SlotNotFoundError(slot_id)

        if slot.teacher_id != teacher_id:
            raise TeacherSlotAccessError(slot_id)

        return await self._repository.list_teacher_slot_bookings(
            slot_id=slot_id,
            status=status,
            skip=skip,
            limit=limit,
        )

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

        if booking.status != BookingStatus.ACTIVE:
            raise BookingStatusTransitionError(
                booking_id,
                booking.status,
                BookingStatus.CANCELLED,
            )

        await self._repository.update_booking_status(booking, BookingStatus.CANCELLED)

    async def create_review(
        self,
        *,
        booking_id: int,
        student_id: int,
        rating: int,
        comment: str | None,
    ) -> Review:
        student = await self._repository.get_student_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        booking = await self._repository.get_booking_by_id(booking_id)
        if booking is None:
            raise BookingNotFoundError(booking_id)

        if booking.student_id != student_id:
            raise ReviewNotAllowedError

        if booking.status != BookingStatus.COMPLETED:
            raise ReviewNotAllowedError

        slot = await self._repository.get_slot_by_id(booking.slot_id)
        if slot is None:
            raise SlotNotFoundError(booking.slot_id)

        existing_review = await self._repository.get_review_by_booking(booking_id)
        if existing_review is not None:
            raise ReviewAlreadyExistsError(booking_id=booking_id)

        return await self._repository.create_review(
            booking_id=booking_id,
            teacher_id=slot.teacher_id,
            student_id=student_id,
            rating=rating,
            comment=comment,
        )

    async def list_reviews(
        self,
        teacher_id: int | None = None,
        discipline_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ReviewProjection]:
        if teacher_id is not None:
            teacher = await self._repository.get_teacher_by_id(teacher_id)
            if teacher is None:
                raise TeacherNotFoundError(teacher_id)

        if discipline_id is not None:
            discipline = await self._repository.get_discipline_by_id(discipline_id)
            if discipline is None:
                raise DisciplineNotFoundError(discipline_id)

        return await self._repository.list_reviews(
            teacher_id=teacher_id,
            discipline_id=discipline_id,
            skip=skip,
            limit=limit,
        )

    async def complete_slot_bookings_for_teacher(
        self,
        teacher_id: int,
        slot_id: int,
    ) -> int:
        slot = await self._repository.get_slot_by_id(slot_id)
        if slot is None:
            raise SlotNotFoundError(slot_id)

        if slot.teacher_id != teacher_id:
            raise TeacherSlotAccessError(slot_id)

        return await self._repository.complete_active_bookings_for_slot(slot_id)

    async def cancel_booking_for_teacher(
        self,
        teacher_id: int,
        slot_id: int,
        booking_id: int,
    ) -> Booking:
        slot = await self._repository.get_slot_by_id(slot_id)
        if slot is None:
            raise SlotNotFoundError(slot_id)

        if slot.teacher_id != teacher_id:
            raise TeacherSlotAccessError(slot_id)

        booking = await self._repository.get_booking_by_id(booking_id)
        if booking is None:
            raise BookingNotFoundError(booking_id)

        if booking.slot_id != slot_id:
            raise BookingSlotMismatchError(booking_id, slot_id)

        if booking.status != BookingStatus.ACTIVE:
            raise BookingStatusTransitionError(
                booking_id,
                booking.status,
                BookingStatus.CANCELLED,
            )

        return await self._repository.update_booking_status(booking, BookingStatus.CANCELLED)

    async def complete_booking_for_teacher(
        self,
        teacher_id: int,
        slot_id: int,
        booking_id: int,
    ) -> Booking:
        slot = await self._repository.get_slot_by_id(slot_id)
        if slot is None:
            raise SlotNotFoundError(slot_id)

        if slot.teacher_id != teacher_id:
            raise TeacherSlotAccessError(slot_id)

        booking = await self._repository.get_booking_by_id(booking_id)
        if booking is None:
            raise BookingNotFoundError(booking_id)

        if booking.slot_id != slot_id:
            raise BookingSlotMismatchError(booking_id, slot_id)

        if booking.status != BookingStatus.ACTIVE:
            raise BookingStatusTransitionError(
                booking_id,
                booking.status,
                BookingStatus.COMPLETED,
            )

        return await self._repository.update_booking_status(booking, BookingStatus.COMPLETED)

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
