from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import EmailStr

from app.application.dto.enrollment_dto import (
    AnalyticsOverviewReadDTO,
    AvailableSlotReadDTO,
    BookingCreateDTO,
    BookingDetailsReadDTO,
    BookingReadDTO,
    CityCreateDTO,
    CityReadDTO,
    DisciplineAnalyticsReadDTO,
    DisciplineCreateDTO,
    DisciplineReadDTO,
    ReviewCreateDTO,
    ReviewListReadDTO,
    ReviewReadDTO,
    StudentCreateDTO,
    StudentReadDTO,
    TeacherAnalyticsReadDTO,
    TeacherCreateDTO,
    TeacherReadDTO,
    TeacherSlotCreateDTO,
    TeacherSlotReadDTO,
)
from app.application.interfaces.enrollment_repository import (
    AnalyticsOverviewProjection,
    AvailableSlotProjection,
    BookingProjection,
    DisciplineAnalyticsProjection,
    ReviewProjection,
    TeacherRatingSummary,
    TeacherAnalyticsProjection,
)
from app.application.services.enrollment_service import (
    AnalyticsFilterRangeError,
    ReviewAlreadyExistsError,
    ReviewNotAllowedError,
    BookingStatusTransitionError,
    BookingOwnershipError,
    BookingNotFoundError,
    CityNotFoundError,
    DisciplineNotFoundError,
    DuplicateBookingError,
    EnrollmentService,
    SlotFullError,
    SlotIsInactiveError,
    SlotNotFoundError,
    StudentTimeConflictError,
    StudentNotFoundError,
    TeacherNotFoundError,
)
from app.domain.entities.teacher import Teacher
from app.domain.entities.booking import BookingStatus
from app.domain.entities.user_account import UserAccount, UserRole
from app.presentation.api.dependencies import get_enrollment_service
from app.presentation.api.security import get_student_user, require_roles

router = APIRouter(prefix="/enrollment", tags=["enrollment"])

EnrollmentServiceDependency = Annotated[EnrollmentService, Depends(get_enrollment_service)]
AdminUserDependency = Annotated[UserAccount, Depends(require_roles(UserRole.ADMIN))]
StudentUserDependency = Annotated[UserAccount, Depends(get_student_user)]
StudentOnlyUserDependency = Annotated[UserAccount, Depends(require_roles(UserRole.STUDENT))]


def _teacher_to_dto(
    teacher: Teacher,
    rating_summary: TeacherRatingSummary | None = None,
) -> TeacherReadDTO:
    return TeacherReadDTO(
        id=teacher.id,
        full_name=teacher.full_name,
        city_id=teacher.city_id,
        discipline_ids=sorted(link.discipline_id for link in teacher.discipline_links),
        average_rating=rating_summary.average_rating if rating_summary is not None else None,
        reviews_count=rating_summary.reviews_count if rating_summary is not None else 0,
    )


def _available_slot_to_dto(slot: AvailableSlotProjection) -> AvailableSlotReadDTO:
    available_seats = max(slot.capacity - slot.reserved_seats, 0)
    return AvailableSlotReadDTO(
        slot_id=slot.slot_id,
        teacher_id=slot.teacher_id,
        teacher_name=slot.teacher_name,
        city_id=slot.city_id,
        city_name=slot.city_name,
        discipline_id=slot.discipline_id,
        discipline_name=slot.discipline_name,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        description=slot.description,
        capacity=slot.capacity,
        reserved_seats=slot.reserved_seats,
        available_seats=available_seats,
    )


def _booking_to_dto(booking: BookingProjection) -> BookingDetailsReadDTO:
    return BookingDetailsReadDTO(
        booking_id=booking.booking_id,
        student_id=booking.student_id,
        student_name=booking.student_name,
        student_email=booking.student_email,
        slot_id=booking.slot_id,
        teacher_id=booking.teacher_id,
        teacher_name=booking.teacher_name,
        city_id=booking.city_id,
        city_name=booking.city_name,
        discipline_id=booking.discipline_id,
        discipline_name=booking.discipline_name,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        description=booking.description,
        status=booking.status,
        has_review=booking.has_review,
        created_at=booking.created_at,
    )


def _review_to_dto(review) -> ReviewReadDTO:
    return ReviewReadDTO.model_validate(review)


def _review_projection_to_dto(review: ReviewProjection) -> ReviewListReadDTO:
    return ReviewListReadDTO(
        review_id=review.review_id,
        booking_id=review.booking_id,
        teacher_id=review.teacher_id,
        teacher_name=review.teacher_name,
        student_id=review.student_id,
        student_name=review.student_name,
        discipline_id=review.discipline_id,
        discipline_name=review.discipline_name,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


def _overview_to_dto(overview: AnalyticsOverviewProjection) -> AnalyticsOverviewReadDTO:
    return AnalyticsOverviewReadDTO(
        total_cities=overview.total_cities,
        total_disciplines=overview.total_disciplines,
        total_teachers=overview.total_teachers,
        total_students=overview.total_students,
        filtered_slots_total=overview.filtered_slots_total,
        filtered_slots_active=overview.filtered_slots_active,
        filtered_bookings_total=overview.filtered_bookings_total,
        filtered_capacity_total=overview.filtered_capacity_total,
        filtered_reserved_seats_total=overview.filtered_reserved_seats_total,
        utilization_rate_percent=overview.utilization_rate_percent,
    )


def _teacher_analytics_to_dto(item: TeacherAnalyticsProjection) -> TeacherAnalyticsReadDTO:
    return TeacherAnalyticsReadDTO(
        teacher_id=item.teacher_id,
        teacher_name=item.teacher_name,
        city_id=item.city_id,
        city_name=item.city_name,
        slots_total=item.slots_total,
        slots_active=item.slots_active,
        bookings_total=item.bookings_total,
        capacity_total=item.capacity_total,
        reserved_seats_total=item.reserved_seats_total,
        utilization_rate_percent=item.utilization_rate_percent,
    )


def _discipline_analytics_to_dto(item: DisciplineAnalyticsProjection) -> DisciplineAnalyticsReadDTO:
    return DisciplineAnalyticsReadDTO(
        discipline_id=item.discipline_id,
        discipline_name=item.discipline_name,
        slots_total=item.slots_total,
        slots_active=item.slots_active,
        bookings_total=item.bookings_total,
        capacity_total=item.capacity_total,
        reserved_seats_total=item.reserved_seats_total,
        utilization_rate_percent=item.utilization_rate_percent,
    )


@router.post("/cities", response_model=CityReadDTO, status_code=status.HTTP_201_CREATED)
async def create_city(
    city_in: CityCreateDTO,
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
) -> CityReadDTO:
    city = await service.create_city(city_in)
    return CityReadDTO.model_validate(city)


@router.get("/cities", response_model=list[CityReadDTO])
async def list_cities(service: EnrollmentServiceDependency) -> list[CityReadDTO]:
    cities = await service.list_cities()
    return [CityReadDTO.model_validate(city) for city in cities]


@router.post("/disciplines", response_model=DisciplineReadDTO, status_code=status.HTTP_201_CREATED)
async def create_discipline(
    discipline_in: DisciplineCreateDTO,
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
) -> DisciplineReadDTO:
    discipline = await service.create_discipline(discipline_in)
    return DisciplineReadDTO.model_validate(discipline)


@router.get("/disciplines", response_model=list[DisciplineReadDTO])
async def list_disciplines(service: EnrollmentServiceDependency) -> list[DisciplineReadDTO]:
    disciplines = await service.list_disciplines()
    return [DisciplineReadDTO.model_validate(discipline) for discipline in disciplines]


@router.post("/teachers", response_model=TeacherReadDTO, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    teacher_in: TeacherCreateDTO,
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
) -> TeacherReadDTO:
    try:
        teacher = await service.create_teacher(teacher_in)
    except (CityNotFoundError, DisciplineNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return _teacher_to_dto(teacher)


@router.get("/teachers", response_model=list[TeacherReadDTO])
async def list_teachers(
    service: EnrollmentServiceDependency,
    city_id: int | None = Query(default=None, gt=0),
    discipline_id: int | None = Query(default=None, gt=0),
    search_query: str | None = Query(default=None, min_length=1, max_length=255),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TeacherReadDTO]:
    try:
        teachers = await service.list_teachers(
            city_id=city_id,
            discipline_id=discipline_id,
            search_query=search_query,
            skip=skip,
            limit=limit,
        )
    except (CityNotFoundError, DisciplineNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    ratings = await service.get_teacher_rating_summaries([teacher.id for teacher in teachers])
    return [_teacher_to_dto(teacher, ratings.get(teacher.id)) for teacher in teachers]


@router.post("/students", response_model=StudentReadDTO, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_in: StudentCreateDTO,
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
) -> StudentReadDTO:
    try:
        student = await service.create_student(student_in)
    except CityNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return StudentReadDTO.model_validate(student)


@router.get("/students", response_model=list[StudentReadDTO])
async def list_students(
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
    city_id: int | None = Query(default=None, gt=0),
    email: EmailStr | None = Query(default=None, max_length=255),
) -> list[StudentReadDTO]:
    try:
        students = await service.list_students(city_id=city_id, email=email)
    except CityNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return [StudentReadDTO.model_validate(student) for student in students]


@router.post("/slots", response_model=TeacherSlotReadDTO, status_code=status.HTTP_201_CREATED)
async def create_slot(
    slot_in: TeacherSlotCreateDTO,
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
) -> TeacherSlotReadDTO:
    try:
        slot = await service.create_slot(slot_in)
    except (TeacherNotFoundError, DisciplineNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return TeacherSlotReadDTO.model_validate(slot)


@router.get("/slots/available", response_model=list[AvailableSlotReadDTO])
async def list_available_slots(
    service: EnrollmentServiceDependency,
    city_id: int | None = Query(default=None, gt=0),
    discipline_id: int | None = Query(default=None, gt=0),
    teacher_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AvailableSlotReadDTO]:
    try:
        slots = await service.list_available_slots(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            skip=skip,
            limit=limit,
        )
    except (CityNotFoundError, DisciplineNotFoundError, TeacherNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return [_available_slot_to_dto(slot) for slot in slots]


@router.get("/analytics/overview", response_model=AnalyticsOverviewReadDTO)
async def get_analytics_overview(
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
    city_id: int | None = Query(default=None, gt=0),
    discipline_id: int | None = Query(default=None, gt=0),
    teacher_id: int | None = Query(default=None, gt=0),
    starts_from: datetime | None = Query(default=None),
    ends_to: datetime | None = Query(default=None),
) -> AnalyticsOverviewReadDTO:
    try:
        overview = await service.get_overview_analytics(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )
    except (CityNotFoundError, DisciplineNotFoundError, TeacherNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AnalyticsFilterRangeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return _overview_to_dto(overview)


@router.get("/analytics/teachers", response_model=list[TeacherAnalyticsReadDTO])
async def list_teacher_analytics(
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
    city_id: int | None = Query(default=None, gt=0),
    discipline_id: int | None = Query(default=None, gt=0),
    teacher_id: int | None = Query(default=None, gt=0),
    starts_from: datetime | None = Query(default=None),
    ends_to: datetime | None = Query(default=None),
) -> list[TeacherAnalyticsReadDTO]:
    try:
        rows = await service.list_teacher_analytics(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )
    except (CityNotFoundError, DisciplineNotFoundError, TeacherNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AnalyticsFilterRangeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return [_teacher_analytics_to_dto(item) for item in rows]


@router.get("/analytics/disciplines", response_model=list[DisciplineAnalyticsReadDTO])
async def list_discipline_analytics(
    service: EnrollmentServiceDependency,
    _: AdminUserDependency,
    city_id: int | None = Query(default=None, gt=0),
    discipline_id: int | None = Query(default=None, gt=0),
    teacher_id: int | None = Query(default=None, gt=0),
    starts_from: datetime | None = Query(default=None),
    ends_to: datetime | None = Query(default=None),
) -> list[DisciplineAnalyticsReadDTO]:
    try:
        rows = await service.list_discipline_analytics(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )
    except (CityNotFoundError, DisciplineNotFoundError, TeacherNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AnalyticsFilterRangeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return [_discipline_analytics_to_dto(item) for item in rows]


@router.post("/bookings", response_model=BookingReadDTO, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_in: BookingCreateDTO,
    service: EnrollmentServiceDependency,
    current_user: StudentUserDependency,
) -> BookingReadDTO:
    student_id = booking_in.student_id
    if current_user.role == UserRole.STUDENT:
        if current_user.student_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student account is not linked to student profile.",
            )
        student_id = current_user.student_id

    booking_payload = BookingCreateDTO(student_id=student_id, slot_id=booking_in.slot_id)

    try:
        booking = await service.create_booking(booking_payload)
    except (StudentNotFoundError, SlotNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (SlotIsInactiveError, SlotFullError, DuplicateBookingError, StudentTimeConflictError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return BookingReadDTO.model_validate(booking)


@router.get("/bookings", response_model=list[BookingDetailsReadDTO])
async def list_bookings(
    service: EnrollmentServiceDependency,
    current_user: StudentUserDependency,
    student_id: int | None = Query(default=None, gt=0),
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[BookingDetailsReadDTO]:
    effective_student_id = student_id
    if current_user.role == UserRole.STUDENT:
        if current_user.student_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student account is not linked to student profile.",
            )
        effective_student_id = current_user.student_id

    try:
        bookings = await service.list_bookings(
            student_id=effective_student_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )
    except StudentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return [_booking_to_dto(booking) for booking in bookings]


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: int,
    service: EnrollmentServiceDependency,
    current_user: StudentUserDependency,
) -> Response:
    student_id: int | None = None
    if current_user.role == UserRole.STUDENT:
        if current_user.student_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student account is not linked to student profile.",
            )
        student_id = current_user.student_id

    try:
        await service.cancel_booking(booking_id, student_id=student_id)
    except BookingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BookingOwnershipError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except BookingStatusTransitionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reviews", response_model=ReviewReadDTO, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_in: ReviewCreateDTO,
    service: EnrollmentServiceDependency,
    current_user: StudentOnlyUserDependency,
) -> ReviewReadDTO:
    if current_user.student_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student account is not linked to student profile.",
        )

    try:
        review = await service.create_review(
            booking_id=review_in.booking_id,
            student_id=current_user.student_id,
            rating=review_in.rating,
            comment=review_in.comment,
        )
    except (BookingNotFoundError, SlotNotFoundError, StudentNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (ReviewNotAllowedError, ReviewAlreadyExistsError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return _review_to_dto(review)


@router.get("/reviews", response_model=list[ReviewListReadDTO])
async def list_reviews(
    service: EnrollmentServiceDependency,
    teacher_id: int | None = Query(default=None, gt=0),
    discipline_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ReviewListReadDTO]:
    try:
        rows = await service.list_reviews(
            teacher_id=teacher_id,
            discipline_id=discipline_id,
            skip=skip,
            limit=limit,
        )
    except (TeacherNotFoundError, DisciplineNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return [_review_projection_to_dto(row) for row in rows]
