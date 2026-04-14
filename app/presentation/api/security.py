from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import InvalidTokenError, decode_access_token
from app.domain.entities.user_account import UserAccount, UserRole
from app.presentation.api.dependencies import get_auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service=Depends(get_auth_service),
) -> UserAccount:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (InvalidTokenError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = await auth_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*roles: UserRole):
    async def role_dependency(
        current_user: Annotated[UserAccount, Depends(get_current_user)],
    ) -> UserAccount:
        if current_user.role not in roles:
            allowed = ", ".join(role.value for role in roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {allowed}.",
            )
        return current_user

    return role_dependency


async def get_student_user(
    current_user: Annotated[
        UserAccount,
        Depends(require_roles(UserRole.STUDENT, UserRole.ADMIN)),
    ],
) -> UserAccount:
    if current_user.role == UserRole.STUDENT and current_user.student_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student account is not linked to student profile.",
        )
    return current_user


async def get_teacher_user(
    current_user: Annotated[
        UserAccount,
        Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
    ],
) -> UserAccount:
    if current_user.role == UserRole.TEACHER and current_user.teacher_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher account is not linked to teacher profile.",
        )
    return current_user
