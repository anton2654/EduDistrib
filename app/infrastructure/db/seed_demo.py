from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.booking import Booking
from app.domain.entities.city import City
from app.domain.entities.discipline import Discipline
from app.domain.entities.student import Student
from app.domain.entities.teacher import Teacher
from app.domain.entities.teacher_discipline import TeacherDiscipline
from app.domain.entities.teacher_slot import TeacherSlot
from app.domain.entities.task import Task
from app.domain.entities.user_account import UserAccount, UserRole
from app.core.security import hash_password
from app.infrastructure.db.engine import engine
from app.infrastructure.db.session import async_session_factory


async def _get_or_create_city(
    session: AsyncSession,
    name: str,
    stats: dict[str, int],
) -> City:
    city = (await session.execute(select(City).where(City.name == name))).scalar_one_or_none()
    if city is not None:
        return city

    city = City(name=name)
    session.add(city)
    await session.flush()
    stats["cities_created"] += 1
    return city


async def _get_or_create_discipline(
    session: AsyncSession,
    name: str,
    stats: dict[str, int],
) -> Discipline:
    discipline = (
        await session.execute(select(Discipline).where(Discipline.name == name))
    ).scalar_one_or_none()
    if discipline is not None:
        return discipline

    discipline = Discipline(name=name)
    session.add(discipline)
    await session.flush()
    stats["disciplines_created"] += 1
    return discipline


async def _get_or_create_teacher(
    session: AsyncSession,
    full_name: str,
    city_id: int,
    stats: dict[str, int],
) -> Teacher:
    teacher = (
        await session.execute(
            select(Teacher).where(
                Teacher.full_name == full_name,
                Teacher.city_id == city_id,
            ),
        )
    ).scalar_one_or_none()
    if teacher is not None:
        return teacher

    teacher = Teacher(full_name=full_name, city_id=city_id)
    session.add(teacher)
    await session.flush()
    stats["teachers_created"] += 1
    return teacher


async def _ensure_teacher_discipline(
    session: AsyncSession,
    teacher_id: int,
    discipline_id: int,
    stats: dict[str, int],
) -> None:
    link = (
        await session.execute(
            select(TeacherDiscipline).where(
                TeacherDiscipline.teacher_id == teacher_id,
                TeacherDiscipline.discipline_id == discipline_id,
            ),
        )
    ).scalar_one_or_none()

    if link is not None:
        return

    session.add(TeacherDiscipline(teacher_id=teacher_id, discipline_id=discipline_id))
    await session.flush()
    stats["teacher_discipline_links_created"] += 1


async def _get_or_create_student(
    session: AsyncSession,
    full_name: str,
    email: str,
    city_id: int,
    stats: dict[str, int],
) -> Student:
    student = (
        await session.execute(select(Student).where(Student.email == email))
    ).scalar_one_or_none()
    if student is not None:
        return student

    student = Student(full_name=full_name, email=email, city_id=city_id)
    session.add(student)
    await session.flush()
    stats["students_created"] += 1
    return student


async def _ensure_slot(
    session: AsyncSession,
    teacher_id: int,
    discipline_id: int,
    starts_at: datetime,
    ends_at: datetime,
    capacity: int,
    stats: dict[str, int],
) -> TeacherSlot:
    slot = (
        await session.execute(
            select(TeacherSlot).where(
                TeacherSlot.teacher_id == teacher_id,
                TeacherSlot.discipline_id == discipline_id,
                TeacherSlot.starts_at == starts_at,
                TeacherSlot.ends_at == ends_at,
            ),
        )
    ).scalar_one_or_none()

    if slot is not None:
        return slot

    slot = TeacherSlot(
        teacher_id=teacher_id,
        discipline_id=discipline_id,
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=capacity,
        is_active=True,
    )
    session.add(slot)
    await session.flush()
    stats["slots_created"] += 1
    return slot


async def _count_rows(session: AsyncSession, model: type) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


async def _get_account_by_username(session: AsyncSession, username: str) -> UserAccount | None:
    return (
        await session.execute(select(UserAccount).where(UserAccount.username == username))
    ).scalar_one_or_none()


async def _get_account_by_profile(
    session: AsyncSession,
    *,
    student_id: int | None,
    teacher_id: int | None,
) -> UserAccount | None:
    if student_id is not None:
        return (
            await session.execute(
                select(UserAccount).where(UserAccount.student_id == student_id),
            )
        ).scalar_one_or_none()

    if teacher_id is not None:
        return (
            await session.execute(
                select(UserAccount).where(UserAccount.teacher_id == teacher_id),
            )
        ).scalar_one_or_none()

    return None


async def _ensure_account(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    role: UserRole,
    stats: dict[str, int],
    student_id: int | None = None,
    teacher_id: int | None = None,
) -> UserAccount:
    account = await _get_account_by_username(session, username)
    if account is None:
        account = await _get_account_by_profile(
            session,
            student_id=student_id,
            teacher_id=teacher_id,
        )

    if account is not None:
        updated = False

        if account.username != username:
            account.username = username
            updated = True

        if account.role != role:
            account.role = role
            updated = True

        if account.student_id != student_id:
            account.student_id = student_id
            updated = True

        if account.teacher_id != teacher_id:
            account.teacher_id = teacher_id
            updated = True

        if updated:
            await session.flush()

        return account

    account = UserAccount(
        username=username,
        password_hash=hash_password(password),
        role=role,
        student_id=student_id,
        teacher_id=teacher_id,
    )
    session.add(account)
    await session.flush()
    stats["accounts_created"] += 1
    return account


async def seed_demo_data() -> None:
    stats: dict[str, int] = {
        "cities_created": 0,
        "disciplines_created": 0,
        "teachers_created": 0,
        "teacher_discipline_links_created": 0,
        "students_created": 0,
        "slots_created": 0,
        "accounts_created": 0,
    }

    async with async_session_factory() as session:
        async with session.begin():
            city_names = ["Lviv", "Kyiv", "Odesa"]
            discipline_names = ["Mathematics", "Programming", "English"]

            cities = {
                name: await _get_or_create_city(session, name, stats) for name in city_names
            }
            disciplines = {
                name: await _get_or_create_discipline(session, name, stats)
                for name in discipline_names
            }

            teacher_specs = [
                {
                    "full_name": "Ivan Petrenko",
                    "city": "Lviv",
                    "disciplines": ["Mathematics", "Programming"],
                },
                {
                    "full_name": "Olena Shevchenko",
                    "city": "Kyiv",
                    "disciplines": ["English"],
                },
                {
                    "full_name": "Maria Koval",
                    "city": "Odesa",
                    "disciplines": ["Programming"],
                },
            ]

            teachers: dict[str, Teacher] = {}
            for spec in teacher_specs:
                teacher = await _get_or_create_teacher(
                    session,
                    full_name=spec["full_name"],
                    city_id=cities[spec["city"]].id,
                    stats=stats,
                )
                teachers[spec["full_name"]] = teacher

                for discipline_name in spec["disciplines"]:
                    await _ensure_teacher_discipline(
                        session,
                        teacher_id=teacher.id,
                        discipline_id=disciplines[discipline_name].id,
                        stats=stats,
                    )

            student_specs = [
                {"full_name": "Andriy Melnyk", "email": "andriy@example.com", "city": "Lviv"},
                {"full_name": "Iryna Bondar", "email": "iryna@example.com", "city": "Kyiv"},
                {"full_name": "Taras Shevchuk", "email": "taras@example.com", "city": "Odesa"},
            ]

            for spec in student_specs:
                await _get_or_create_student(
                    session,
                    full_name=spec["full_name"],
                    email=spec["email"],
                    city_id=cities[spec["city"]].id,
                    stats=stats,
                )

            students = {
                student.email: student
                for student in (
                    await session.execute(select(Student).order_by(Student.id))
                ).scalars()
            }

            slot_specs = [
                {
                    "teacher": "Ivan Petrenko",
                    "discipline": "Mathematics",
                    "starts_at": datetime(2030, 5, 1, 10, 0, tzinfo=timezone.utc),
                    "ends_at": datetime(2030, 5, 1, 11, 30, tzinfo=timezone.utc),
                    "capacity": 3,
                },
                {
                    "teacher": "Ivan Petrenko",
                    "discipline": "Programming",
                    "starts_at": datetime(2030, 5, 2, 14, 0, tzinfo=timezone.utc),
                    "ends_at": datetime(2030, 5, 2, 15, 30, tzinfo=timezone.utc),
                    "capacity": 2,
                },
                {
                    "teacher": "Olena Shevchenko",
                    "discipline": "English",
                    "starts_at": datetime(2030, 5, 3, 12, 0, tzinfo=timezone.utc),
                    "ends_at": datetime(2030, 5, 3, 13, 30, tzinfo=timezone.utc),
                    "capacity": 4,
                },
                {
                    "teacher": "Maria Koval",
                    "discipline": "Programming",
                    "starts_at": datetime(2030, 5, 4, 16, 0, tzinfo=timezone.utc),
                    "ends_at": datetime(2030, 5, 4, 17, 30, tzinfo=timezone.utc),
                    "capacity": 3,
                },
            ]

            for spec in slot_specs:
                await _ensure_slot(
                    session,
                    teacher_id=teachers[spec["teacher"]].id,
                    discipline_id=disciplines[spec["discipline"]].id,
                    starts_at=spec["starts_at"],
                    ends_at=spec["ends_at"],
                    capacity=spec["capacity"],
                    stats=stats,
                )

            await _ensure_account(
                session,
                username="admin",
                password="admin12345",
                role=UserRole.ADMIN,
                stats=stats,
            )

            await _ensure_account(
                session,
                username="teacher_ivan",
                password="teacher123",
                role=UserRole.TEACHER,
                teacher_id=teachers["Ivan Petrenko"].id,
                stats=stats,
            )
            await _ensure_account(
                session,
                username="teacher_olena",
                password="teacher123",
                role=UserRole.TEACHER,
                teacher_id=teachers["Olena Shevchenko"].id,
                stats=stats,
            )
            await _ensure_account(
                session,
                username="teacher_maria",
                password="teacher123",
                role=UserRole.TEACHER,
                teacher_id=teachers["Maria Koval"].id,
                stats=stats,
            )

            await _ensure_account(
                session,
                username="student_andriy",
                password="student123",
                role=UserRole.STUDENT,
                student_id=students["andriy@example.com"].id,
                stats=stats,
            )
            await _ensure_account(
                session,
                username="student_iryna",
                password="student123",
                role=UserRole.STUDENT,
                student_id=students["iryna@example.com"].id,
                stats=stats,
            )
            await _ensure_account(
                session,
                username="student_taras",
                password="student123",
                role=UserRole.STUDENT,
                student_id=students["taras@example.com"].id,
                stats=stats,
            )

        total_cities = await _count_rows(session, City)
        total_disciplines = await _count_rows(session, Discipline)
        total_teachers = await _count_rows(session, Teacher)
        total_students = await _count_rows(session, Student)
        total_slots = await _count_rows(session, TeacherSlot)
        total_bookings = await _count_rows(session, Booking)
        total_tasks = await _count_rows(session, Task)
        total_accounts = await _count_rows(session, UserAccount)

    print("Seed completed.")
    print("Created in this run:")
    print(f"  cities: {stats['cities_created']}")
    print(f"  disciplines: {stats['disciplines_created']}")
    print(f"  teachers: {stats['teachers_created']}")
    print(f"  teacher-discipline links: {stats['teacher_discipline_links_created']}")
    print(f"  students: {stats['students_created']}")
    print(f"  slots: {stats['slots_created']}")
    print(f"  accounts: {stats['accounts_created']}")
    print("Totals in database:")
    print(f"  cities: {total_cities}")
    print(f"  disciplines: {total_disciplines}")
    print(f"  teachers: {total_teachers}")
    print(f"  students: {total_students}")
    print(f"  slots: {total_slots}")
    print(f"  bookings: {total_bookings}")
    print(f"  tasks: {total_tasks}")
    print(f"  accounts: {total_accounts}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
