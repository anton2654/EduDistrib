from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto.auth_dto import (
    AccountReadDTO,
    AdminBootstrapDTO,
    LoginDTO,
    StudentRegisterDTO,
    TeacherAccountCreateDTO,
    TokenReadDTO,
)
from app.application.services.auth_service import (
    AuthService,
    BootstrapAlreadyCompletedError,
    CityNotFoundForAuthError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    TeacherNotFoundForAuthError,
    UsernameAlreadyExistsError,
)
from app.domain.entities.user_account import UserAccount, UserRole
from app.presentation.api.dependencies import get_auth_service
from app.presentation.api.security import get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["auth"])

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDependency = Annotated[UserAccount, Depends(get_current_user)]
AdminUserDependency = Annotated[
    UserAccount,
    Depends(require_roles(UserRole.ADMIN)),
]


def _to_account_read(user: UserAccount) -> AccountReadDTO:
    return AccountReadDTO(
        user_id=user.id,
        username=user.username,
        role=user.role,
        student_id=user.student_id,
        teacher_id=user.teacher_id,
        created_at=user.created_at,
    )


@router.post(
    "/bootstrap-admin",
    response_model=TokenReadDTO,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_admin(
    admin_in: AdminBootstrapDTO,
    service: AuthServiceDependency,
) -> TokenReadDTO:
    try:
        return await service.bootstrap_admin(admin_in)
    except BootstrapAlreadyCompletedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except UsernameAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/register/student",
    response_model=TokenReadDTO,
    status_code=status.HTTP_201_CREATED,
)
async def register_student(
    student_in: StudentRegisterDTO,
    service: AuthServiceDependency,
) -> TokenReadDTO:
    try:
        return await service.register_student(student_in)
    except CityNotFoundForAuthError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (UsernameAlreadyExistsError, EmailAlreadyExistsError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/register/teacher", response_model=AccountReadDTO, status_code=status.HTTP_201_CREATED)
async def register_teacher_account(
    teacher_account_in: TeacherAccountCreateDTO,
    service: AuthServiceDependency,
    _: AdminUserDependency,
) -> AccountReadDTO:
    try:
        return await service.register_teacher_account(teacher_account_in)
    except TeacherNotFoundForAuthError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except UsernameAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/login", response_model=TokenReadDTO)
async def login(
    login_in: LoginDTO,
    service: AuthServiceDependency,
) -> TokenReadDTO:
    try:
        return await service.login(login_in)
    except InvalidCredentialsError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@router.get("/me", response_model=AccountReadDTO)
async def me(current_user: CurrentUserDependency) -> AccountReadDTO:
    return _to_account_read(current_user)


@router.get("/accounts", response_model=list[AccountReadDTO])
async def list_accounts(
    service: AuthServiceDependency,
    _: AdminUserDependency,
) -> list[AccountReadDTO]:
    return await service.list_accounts()
