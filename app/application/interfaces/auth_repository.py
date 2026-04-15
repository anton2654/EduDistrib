from abc import ABC, abstractmethod

from app.application.dto.auth_dto import StudentRegisterDTO
from app.domain.entities.city import City
from app.domain.entities.student import Student
from app.domain.entities.teacher import Teacher
from app.domain.entities.user_account import UserAccount, UserRole


class AuthRepositoryInterface(ABC):
    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> UserAccount | None:
        raise NotImplementedError

    @abstractmethod
    async def get_user_by_username(self, username: str) -> UserAccount | None:
        raise NotImplementedError

    @abstractmethod
    async def list_users(self, *, skip: int = 0, limit: int = 50) -> list[UserAccount]:
        raise NotImplementedError

    @abstractmethod
    async def count_admins(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_city_by_id(self, city_id: int) -> City | None:
        raise NotImplementedError

    @abstractmethod
    async def get_teacher_by_id(self, teacher_id: int) -> Teacher | None:
        raise NotImplementedError

    @abstractmethod
    async def get_student_by_email(self, email: str) -> Student | None:
        raise NotImplementedError

    @abstractmethod
    async def create_student(self, student_in: StudentRegisterDTO) -> Student:
        raise NotImplementedError

    @abstractmethod
    async def create_user_account(
        self,
        *,
        username: str,
        password_hash: str,
        role: UserRole,
        student_id: int | None = None,
        teacher_id: int | None = None,
    ) -> UserAccount:
        raise NotImplementedError
