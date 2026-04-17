from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.application.dto.enrollment_dto import (
    BookingReadDTO,
    TeacherSlotBulkBookingActionReadDTO,
    TeacherSlotBookingReadDTO,
    TeacherSlotDetailsReadDTO,
    TeacherSlotManageCreateDTO,
    TeacherSlotReadDTO,
    TeacherSlotUpdateDTO,
)
from app.application.interfaces.enrollment_repository import TeacherSlotBookingProjection, TeacherSlotProjection
from app.application.services.enrollment_service import (
    BookingNotFoundError,
    BookingSlotMismatchError,
    BookingStatusTransitionError,
    DisciplineNotFoundError,
    EnrollmentService,
    SlotNotFoundError,
    SlotCapacityBelowReservedError,
    SlotUpdateLockedByActiveBookingsError,
    SlotTimeRangeError,
    TeacherNotFoundError,
    TeacherSlotAccessError,
)
from app.domain.entities.booking import BookingStatus
from app.domain.entities.user_account import UserAccount, UserRole
from app.presentation.api.dependencies import get_enrollment_service
from app.presentation.api.security import require_roles

router = APIRouter(prefix="/teacher/slots", tags=["teacher-slots"])

EnrollmentServiceDependency = Annotated[EnrollmentService, Depends(get_enrollment_service)]
TeacherUserDependency = Annotated[UserAccount, Depends(require_roles(UserRole.TEACHER))]


def _to_teacher_slot_details(slot: TeacherSlotProjection) -> TeacherSlotDetailsReadDTO:
    available_seats = max(slot.capacity - slot.reserved_seats, 0)
    return TeacherSlotDetailsReadDTO(
        slot_id=slot.slot_id,
        teacher_id=slot.teacher_id,
        discipline_id=slot.discipline_id,
        discipline_name=slot.discipline_name,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        description=slot.description,
        capacity=slot.capacity,
        reserved_seats=slot.reserved_seats,
        available_seats=available_seats,
        is_active=slot.is_active,
        created_at=slot.created_at,
    )


def _resolve_teacher_id(current_user: UserAccount) -> int:
    if current_user.teacher_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher account is not linked to teacher profile.",
        )

    return current_user.teacher_id


def _to_teacher_slot_booking(slot_booking: TeacherSlotBookingProjection) -> TeacherSlotBookingReadDTO:
    return TeacherSlotBookingReadDTO(
        booking_id=slot_booking.booking_id,
        student_id=slot_booking.student_id,
        student_name=slot_booking.student_name,
        student_email=slot_booking.student_email,
        status=slot_booking.status,
        created_at=slot_booking.created_at,
    )


@router.get("/", response_model=list[TeacherSlotDetailsReadDTO])
async def list_my_slots(
    service: EnrollmentServiceDependency,
    current_user: TeacherUserDependency,
) -> list[TeacherSlotDetailsReadDTO]:
    teacher_id = _resolve_teacher_id(current_user)

    try:
        slots = await service.list_teacher_slots(teacher_id)
    except TeacherNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return [_to_teacher_slot_details(slot) for slot in slots]


@router.post("/", response_model=TeacherSlotReadDTO, status_code=status.HTTP_201_CREATED)
async def create_my_slot(
    slot_in: TeacherSlotManageCreateDTO,
    service: EnrollmentServiceDependency,
    current_user: TeacherUserDependency,
) -> TeacherSlotReadDTO:
    teacher_id = _resolve_teacher_id(current_user)

    try:
        slot = await service.create_slot_for_teacher(teacher_id, slot_in)
    except (TeacherNotFoundError, DisciplineNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return TeacherSlotReadDTO.model_validate(slot)


@router.put("/{slot_id}", response_model=TeacherSlotReadDTO)
async def update_my_slot(
    slot_id: int,
    slot_in: TeacherSlotUpdateDTO,
    service: EnrollmentServiceDependency,
    current_user: TeacherUserDependency,
) -> TeacherSlotReadDTO:
    teacher_id = _resolve_teacher_id(current_user)

    try:
        slot = await service.update_slot_for_teacher(teacher_id, slot_id, slot_in)
    except (SlotNotFoundError, DisciplineNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (
        SlotTimeRangeError,
        SlotCapacityBelowReservedError,
        SlotUpdateLockedByActiveBookingsError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except TeacherSlotAccessError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    return TeacherSlotReadDTO.model_validate(slot)


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_slot(
    slot_id: int,
    service: EnrollmentServiceDependency,
    current_user: TeacherUserDependency,
) -> Response:
    teacher_id = _resolve_teacher_id(current_user)

    try:
        await service.delete_slot_for_teacher(teacher_id, slot_id)
    except SlotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except TeacherSlotAccessError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{slot_id}/bookings", response_model=list[TeacherSlotBookingReadDTO])
async def list_slot_bookings(
    slot_id: int,
    service: EnrollmentServiceDependency,
    current_user: TeacherUserDependency,
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TeacherSlotBookingReadDTO]:
    teacher_id = _resolve_teacher_id(current_user)

    try:
        rows = await service.list_teacher_slot_bookings(
            teacher_id=teacher_id,
            slot_id=slot_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )
    except SlotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except TeacherSlotAccessError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    return [_to_teacher_slot_booking(row) for row in rows]


@router.post("/{slot_id}/bookings/{booking_id}/cancel", response_model=BookingReadDTO)
async def cancel_slot_booking(
    slot_id: int,
    booking_id: int,
    service: EnrollmentServiceDependency,
    current_user: TeacherUserDependency,
) -> BookingReadDTO:
    teacher_id = _resolve_teacher_id(current_user)

    try:
        booking = await service.cancel_booking_for_teacher(
            teacher_id=teacher_id,
            slot_id=slot_id,
            booking_id=booking_id,
        )
    except (SlotNotFoundError, BookingNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except TeacherSlotAccessError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except (BookingSlotMismatchError, BookingStatusTransitionError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return BookingReadDTO.model_validate(booking)


@router.post("/{slot_id}/bookings/{booking_id}/complete", response_model=BookingReadDTO)
async def complete_slot_booking(
    slot_id: int,
    booking_id: int,
    service: EnrollmentServiceDependency,
    current_user: TeacherUserDependency,
) -> BookingReadDTO:
    teacher_id = _resolve_teacher_id(current_user)

    try:
        booking = await service.complete_booking_for_teacher(
            teacher_id=teacher_id,
            slot_id=slot_id,
            booking_id=booking_id,
        )
    except (SlotNotFoundError, BookingNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except TeacherSlotAccessError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except (BookingSlotMismatchError, BookingStatusTransitionError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return BookingReadDTO.model_validate(booking)


@router.post("/{slot_id}/bookings/complete-all", response_model=TeacherSlotBulkBookingActionReadDTO)
async def complete_all_slot_bookings(
    slot_id: int,
    service: EnrollmentServiceDependency,
    current_user: TeacherUserDependency,
) -> TeacherSlotBulkBookingActionReadDTO:
    teacher_id = _resolve_teacher_id(current_user)

    try:
        completed_count = await service.complete_slot_bookings_for_teacher(
            teacher_id=teacher_id,
            slot_id=slot_id,
        )
    except SlotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except TeacherSlotAccessError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    return TeacherSlotBulkBookingActionReadDTO(
        slot_id=slot_id,
        updated_bookings=completed_count,
    )
