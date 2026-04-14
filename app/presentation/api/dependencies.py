from typing import Annotated

from fastapi import Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.auth_repository import AuthRepositoryInterface
from app.application.services.auth_service import AuthService
from app.application.interfaces.enrollment_repository import EnrollmentRepositoryInterface
from app.application.dto.task_dto import TaskCreateDTO, TaskUpdateDTO
from app.application.services.enrollment_service import EnrollmentService
from app.application.interfaces.task_repository import TaskRepositoryInterface
from app.application.services.task_service import TaskService
from app.infrastructure.db.session import get_session
from app.infrastructure.repositories.auth_repository import AuthRepository
from app.infrastructure.repositories.enrollment_repository import EnrollmentRepository
from app.infrastructure.repositories.task_repository import TaskRepository


def get_task_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskRepositoryInterface:
    return TaskRepository(session)


def get_task_service(
    repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)],
) -> TaskService:
    return TaskService(repository)


def get_enrollment_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EnrollmentRepositoryInterface:
    return EnrollmentRepository(session)


def get_enrollment_service(
    repository: Annotated[
        EnrollmentRepositoryInterface,
        Depends(get_enrollment_repository),
    ],
) -> EnrollmentService:
    return EnrollmentService(repository)


def get_auth_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthRepositoryInterface:
    return AuthRepository(session)


def get_auth_service(
    repository: Annotated[AuthRepositoryInterface, Depends(get_auth_repository)],
) -> AuthService:
    return AuthService(repository)


def get_task_create_form(
    title: Annotated[str, Form(min_length=1, max_length=255)],
    description: Annotated[str | None, Form(max_length=2000)] = None,
    is_completed: Annotated[bool, Form()] = False,
) -> TaskCreateDTO:
    return TaskCreateDTO(
        title=title,
        description=description,
        is_completed=is_completed,
    )


def get_task_update_form(
    title: Annotated[str, Form(min_length=1, max_length=255)],
    is_completed: Annotated[bool, Form()],
    description: Annotated[str | None, Form(max_length=2000)] = None,
) -> TaskUpdateDTO:
    return TaskUpdateDTO(
        title=title,
        description=description,
        is_completed=is_completed,
    )