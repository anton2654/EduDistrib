from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from app.application.dto.enrollment_dto import NotificationReadDTO
from app.application.interfaces.enrollment_repository import NotificationProjection
from app.application.services.enrollment_service import (
    EnrollmentService,
    NotificationNotFoundError,
)
from app.domain.entities.user_account import UserAccount
from app.presentation.api.dependencies import get_enrollment_service
from app.presentation.api.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

EnrollmentServiceDependency = Annotated[EnrollmentService, Depends(get_enrollment_service)]
CurrentUserDependency = Annotated[UserAccount, Depends(get_current_user)]


def _notification_to_dto(notification: NotificationProjection) -> NotificationReadDTO:
    return NotificationReadDTO(
        id=notification.id,
        title=notification.title,
        message=notification.message,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


@router.get("/me", response_model=list[NotificationReadDTO])
async def list_my_notifications(
    service: EnrollmentServiceDependency,
    current_user: CurrentUserDependency,
) -> list[NotificationReadDTO]:
    rows = await service.list_user_notifications(current_user.id)
    return [_notification_to_dto(row) for row in rows]


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def clear_my_notifications(
    service: EnrollmentServiceDependency,
    current_user: CurrentUserDependency,
    only_read: bool = Query(default=False),
) -> Response:
    await service.clear_user_notifications(
        user_id=current_user.id,
        only_read=only_read,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{notification_id}/read", response_model=NotificationReadDTO)
async def mark_my_notification_as_read(
    service: EnrollmentServiceDependency,
    current_user: CurrentUserDependency,
    notification_id: int = Path(gt=0),
) -> NotificationReadDTO:
    try:
        row = await service.mark_user_notification_as_read(
            notification_id=notification_id,
            user_id=current_user.id,
        )
    except NotificationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return _notification_to_dto(row)
