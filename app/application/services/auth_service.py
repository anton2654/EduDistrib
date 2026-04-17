from sqlalchemy.exc import IntegrityError

from app.application.dto.auth_dto import (
    AccountReadDTO,
    AccountUpdateDTO,
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


class CurrentPasswordInvalidError(AuthError):
    def __init__(self) -> None:
        super().__init__("Current password is invalid.")


class CityUpdateNotAllowedError(AuthError):
    def __init__(self) -> None:
        super().__init__("City can only be updated for student or teacher accounts.")


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

    async def update_current_account(
        self,
        current_user: UserAccount,
        account_in: AccountUpdateDTO,
    ) -> AccountReadDTO:
        if account_in.new_password is not None:
            if account_in.current_password is None or not verify_password(
                account_in.current_password,
                current_user.password_hash,
            ):
                raise CurrentPasswordInvalidError
            current_user.password_hash = hash_password(account_in.new_password)

        if account_in.city_id is not None:
            city = await self._repository.get_city_by_id(account_in.city_id)
            if city is None:
                raise CityNotFoundForAuthError(account_in.city_id)

            if current_user.role == UserRole.STUDENT:
                if current_user.student is None:
                    raise CityUpdateNotAllowedError
                current_user.student.city_id = account_in.city_id
            elif current_user.role == UserRole.TEACHER:
                if current_user.teacher is None:
                    raise CityUpdateNotAllowedError
                current_user.teacher.city_id = account_in.city_id
            else:
                raise CityUpdateNotAllowedError

        await self._repository.save_changes()

        refreshed_user = await self._repository.get_user_by_id(current_user.id)
        if refreshed_user is None:
            return self._to_account_read(current_user)
        return self._to_account_read(refreshed_user)

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
        full_name: str | None = None
        email: str | None = None
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
