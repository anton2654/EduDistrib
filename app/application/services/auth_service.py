from sqlalchemy.exc import IntegrityError

from app.application.dto.auth_dto import (
    AccountReadDTO,
    AdminBootstrapDTO,
    LoginDTO,
    StudentRegisterDTO,
    TeacherAccountCreateDTO,
    TokenReadDTO,
)
from app.application.interfaces.auth_repository import AuthRepositoryInterface
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.entities.user_account import UserAccount, UserRole


class AuthError(Exception):
    pass


class InvalidCredentialsError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid username or password.")


class UsernameAlreadyExistsError(AuthError):
    def __init__(self, username: str) -> None:
        super().__init__(f"Username '{username}' is already taken.")


class EmailAlreadyExistsError(AuthError):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email '{email}' is already used by another student.")


class CityNotFoundForAuthError(AuthError):
    def __init__(self, city_id: int) -> None:
        super().__init__(f"City with id {city_id} was not found.")


class TeacherNotFoundForAuthError(AuthError):
    def __init__(self, teacher_id: int) -> None:
        super().__init__(f"Teacher with id {teacher_id} was not found.")


class BootstrapAlreadyCompletedError(AuthError):
    def __init__(self) -> None:
        super().__init__("Admin bootstrap has already been completed.")


class AuthService:
    def __init__(self, repository: AuthRepositoryInterface) -> None:
        self._repository = repository

    async def bootstrap_admin(self, admin_in: AdminBootstrapDTO) -> TokenReadDTO:
        admins_count = await self._repository.count_admins()
        if admins_count > 0:
            raise BootstrapAlreadyCompletedError

        existing_user = await self._repository.get_user_by_username(admin_in.username)
        if existing_user is not None:
            raise UsernameAlreadyExistsError(admin_in.username)

        user = await self._repository.create_user_account(
            username=admin_in.username,
            password_hash=hash_password(admin_in.password),
            role=UserRole.ADMIN,
        )
        return self._build_token_response(user)

    async def register_student(self, student_in: StudentRegisterDTO) -> TokenReadDTO:
        city = await self._repository.get_city_by_id(student_in.city_id)
        if city is None:
            raise CityNotFoundForAuthError(student_in.city_id)

        existing_user = await self._repository.get_user_by_username(student_in.username)
        if existing_user is not None:
            raise UsernameAlreadyExistsError(student_in.username)

        existing_student = await self._repository.get_student_by_email(student_in.email)
        if existing_student is not None:
            raise EmailAlreadyExistsError(student_in.email)

        try:
            student = await self._repository.create_student(student_in)
            user = await self._repository.create_user_account(
                username=student_in.username,
                password_hash=hash_password(student_in.password),
                role=UserRole.STUDENT,
                student_id=student.id,
            )
        except IntegrityError as error:
            raise UsernameAlreadyExistsError(student_in.username) from error

        return self._build_token_response(user)

    async def register_teacher_account(
        self,
        teacher_account_in: TeacherAccountCreateDTO,
    ) -> AccountReadDTO:
        teacher = await self._repository.get_teacher_by_id(teacher_account_in.teacher_id)
        if teacher is None:
            raise TeacherNotFoundForAuthError(teacher_account_in.teacher_id)

        existing_user = await self._repository.get_user_by_username(teacher_account_in.username)
        if existing_user is not None:
            raise UsernameAlreadyExistsError(teacher_account_in.username)

        try:
            user = await self._repository.create_user_account(
                username=teacher_account_in.username,
                password_hash=hash_password(teacher_account_in.password),
                role=UserRole.TEACHER,
                teacher_id=teacher_account_in.teacher_id,
            )
        except IntegrityError as error:
            raise UsernameAlreadyExistsError(teacher_account_in.username) from error

        return self._to_account_read(user)

    async def login(self, login_in: LoginDTO) -> TokenReadDTO:
        user = await self._repository.get_user_by_username(login_in.username)
        if user is None:
            raise InvalidCredentialsError

        if not verify_password(login_in.password, user.password_hash):
            raise InvalidCredentialsError

        return self._build_token_response(user)

    async def get_user_by_id(self, user_id: int) -> UserAccount | None:
        return await self._repository.get_user_by_id(user_id)

    async def list_accounts(self, *, skip: int = 0, limit: int = 50) -> list[AccountReadDTO]:
        users = await self._repository.list_users(skip=skip, limit=limit)
        return [self._to_account_read(user) for user in users]

    def _build_token_response(self, user: UserAccount) -> TokenReadDTO:
        token = create_access_token(subject=str(user.id), role=user.role.value)
        return TokenReadDTO(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            role=user.role,
            student_id=user.student_id,
            teacher_id=user.teacher_id,
        )

    @staticmethod
    def _to_account_read(user: UserAccount) -> AccountReadDTO:
        return AccountReadDTO(
            user_id=user.id,
            username=user.username,
            role=user.role,
            student_id=user.student_id,
            teacher_id=user.teacher_id,
            created_at=user.created_at,
        )
