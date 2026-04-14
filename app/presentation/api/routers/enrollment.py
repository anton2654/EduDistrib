from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.application.dto.enrollment_dto import (
    AvailableSlotReadDTO,
    BookingCreateDTO,
    BookingDetailsReadDTO,
    BookingReadDTO,
    CityCreateDTO,
    CityReadDTO,
    DisciplineCreateDTO,
    DisciplineReadDTO,
    StudentCreateDTO,
    StudentReadDTO,
    TeacherCreateDTO,
    TeacherReadDTO,
    TeacherSlotCreateDTO,
    TeacherSlotReadDTO,
)
from app.application.interfaces.enrollment_repository import AvailableSlotProjection, BookingProjection
from app.application.services.enrollment_service import (
    BookingOwnershipError,
    BookingNotFoundError,
    CityNotFoundError,
    DisciplineNotFoundError,
    DuplicateBookingError,
    EnrollmentService,
    SlotFullError,
    SlotIsInactiveError,
    SlotNotFoundError,
    StudentNotFoundError,
    TeacherDisciplineMismatchError,
    TeacherNotFoundError,
)
from app.domain.entities.teacher import Teacher
from app.domain.entities.user_account import UserAccount, UserRole
from app.presentation.api.dependencies import get_enrollment_service
from app.presentation.api.security import get_student_user, require_roles

router = APIRouter(prefix="/enrollment", tags=["enrollment"])

EnrollmentServiceDependency = Annotated[EnrollmentService, Depends(get_enrollment_service)]
AdminUserDependency = Annotated[UserAccount, Depends(require_roles(UserRole.ADMIN))]
StudentUserDependency = Annotated[UserAccount, Depends(get_student_user)]


def _teacher_to_dto(teacher: Teacher) -> TeacherReadDTO:
    return TeacherReadDTO(
        id=teacher.id,
        full_name=teacher.full_name,
        city_id=teacher.city_id,
        discipline_ids=sorted(link.discipline_id for link in teacher.discipline_links),
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
        created_at=booking.created_at,
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
) -> list[TeacherReadDTO]:
    try:
        teachers = await service.list_teachers(city_id=city_id, discipline_id=discipline_id)
    except (CityNotFoundError, DisciplineNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return [_teacher_to_dto(teacher) for teacher in teachers]


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
    email: str | None = Query(default=None, min_length=3, max_length=255),
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
    except TeacherDisciplineMismatchError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return TeacherSlotReadDTO.model_validate(slot)


@router.get("/slots/available", response_model=list[AvailableSlotReadDTO])
async def list_available_slots(
    service: EnrollmentServiceDependency,
    city_id: int | None = Query(default=None, gt=0),
    discipline_id: int | None = Query(default=None, gt=0),
    teacher_id: int | None = Query(default=None, gt=0),
) -> list[AvailableSlotReadDTO]:
    try:
        slots = await service.list_available_slots(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
        )
    except (CityNotFoundError, DisciplineNotFoundError, TeacherNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return [_available_slot_to_dto(slot) for slot in slots]


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
    except (SlotIsInactiveError, SlotFullError, DuplicateBookingError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return BookingReadDTO.model_validate(booking)


@router.get("/bookings", response_model=list[BookingDetailsReadDTO])
async def list_bookings(
    service: EnrollmentServiceDependency,
    current_user: StudentUserDependency,
    student_id: int | None = Query(default=None, gt=0),
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
        bookings = await service.list_bookings(student_id=effective_student_id)
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)
