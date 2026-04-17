from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.dto.auth_dto import StudentRegisterDTO
from app.application.interfaces.auth_repository import AuthRepositoryInterface
from app.domain.entities.city import City
from app.domain.entities.student import Student
from app.domain.entities.teacher import Teacher
from app.domain.entities.user_account import UserAccount, UserRole


class AuthRepository(AuthRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_id(self, user_id: int) -> UserAccount | None:
        stmt = (
            select(UserAccount)
            .where(UserAccount.id == user_id)
            .options(
                selectinload(UserAccount.student).selectinload(Student.city),
                selectinload(UserAccount.teacher).selectinload(Teacher.city),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> UserAccount | None:
        stmt = select(UserAccount).where(UserAccount.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(self, *, skip: int = 0, limit: int = 50) -> list[UserAccount]:
        stmt = (
            select(UserAccount)
            .order_by(UserAccount.role, UserAccount.username)
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_admins(self) -> int:
        stmt = select(func.count(UserAccount.id)).where(UserAccount.role == UserRole.ADMIN)
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def get_city_by_id(self, city_id: int) -> City | None:
        return await self._session.get(City, city_id)

    async def get_teacher_by_id(self, teacher_id: int) -> Teacher | None:
        return await self._session.get(Teacher, teacher_id)

    async def get_student_by_email(self, email: str) -> Student | None:
        stmt = select(Student).where(Student.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_student(self, student_in: StudentRegisterDTO) -> Student:
        student = Student(
            full_name=student_in.full_name,
            email=student_in.email,
            city_id=student_in.city_id,
        )
        self._session.add(student)
        await self._session.flush()
        return student

    async def create_user_account(
        self,
        *,
        username: str,
        password_hash: str,
        role: UserRole,
        student_id: int | None = None,
        teacher_id: int | None = None,
    ) -> UserAccount:
        account = UserAccount(
            username=username,
            password_hash=password_hash,
            role=role,
            student_id=student_id,
            teacher_id=teacher_id,
        )
        self._session.add(account)
        await self._session.commit()
        await self._session.refresh(account)
        return account

    async def save_changes(self) -> None:
        await self._session.commit()
