from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.dto.auth_dto import (
    AccountReadDTO,
    AccountUpdateDTO,
    AdminBootstrapDTO,
    LoginDTO,
    StudentRegisterDTO,
    TeacherAccountCreateDTO,
    TokenReadDTO,
)
from app.application.services.auth_service import (
    AuthService,
    BootstrapAlreadyCompletedError,
    CityUpdateNotAllowedError,
    CurrentPasswordInvalidError,
    EmailUpdateNotAllowedError,
    FullNameUpdateNotAllowedError,
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
    full_name: str | None = None
    email: str | None = user.email
    city_id: int | None = None
    city_name: str | None = None

    loaded_student = user.__dict__.get("student")
    loaded_teacher = user.__dict__.get("teacher")

    if loaded_student is not None:
        full_name = loaded_student.full_name
        email = loaded_student.email
        city_id = loaded_student.city_id
        city = loaded_student.__dict__.get("city")
        city_name = city.name if city is not None else None
    elif loaded_teacher is not None:
        full_name = loaded_teacher.full_name
        city_id = loaded_teacher.city_id
        city = loaded_teacher.__dict__.get("city")
        city_name = city.name if city is not None else None

    return AccountReadDTO(
        user_id=user.id,
        username=user.username,
        role=user.role,
        student_id=user.student_id,
        teacher_id=user.teacher_id,
        full_name=full_name,
        email=email,
        city_id=city_id,
        city_name=city_name,
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
    except (UsernameAlreadyExistsError, EmailAlreadyExistsError) as error:
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


@router.patch("/me", response_model=AccountReadDTO)
async def update_me(
    account_in: AccountUpdateDTO,
    service: AuthServiceDependency,
    current_user: CurrentUserDependency,
) -> AccountReadDTO:
    try:
        return await service.update_current_account(current_user, account_in)
    except CurrentPasswordInvalidError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    except CityNotFoundForAuthError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (CityUpdateNotAllowedError, FullNameUpdateNotAllowedError, EmailUpdateNotAllowedError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except (UsernameAlreadyExistsError, EmailAlreadyExistsError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/accounts", response_model=list[AccountReadDTO])
async def list_accounts(
    service: AuthServiceDependency,
    _: AdminUserDependency,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AccountReadDTO]:
    return await service.list_accounts(skip=skip, limit=limit)
