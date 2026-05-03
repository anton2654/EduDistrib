from __future__ import annotations

import asyncio
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.entities.booking import Booking, BookingStatus
from app.domain.entities.city import City
from app.domain.entities.discipline import Discipline
from app.domain.entities.review import Review
from app.domain.entities.student import Student
from app.domain.entities.teacher import Teacher
from app.domain.entities.teacher_discipline import TeacherDiscipline
from app.domain.entities.teacher_slot import TeacherSlot
from app.domain.entities.user_account import UserAccount, UserRole
from app.infrastructure.db.session import async_session_factory

RANDOM_SEED = 20260420

CITY_NAMES = [
    "Київ",
    "Харків",
    "Одеса",
    "Дніпро",
    "Запоріжжя",
    "Львів",
    "Полтава",
    "Чернігів",
    "Черкаси",
    "Житомир",
    "Суми",
    "Хмельницький",
    "Тернопіль",
]

DISCIPLINE_NAMES = [
    "Математика",
    "Програмування",
    "Англійська",
    "Географія",
    "Біологія",
    "Хімія",
    "Фізика",
    "Українська мова",
    "Українська література",
    "Зарубіжна література",
    "Німецька",
    "Французька",
]

POSITIVE_REVIEW_PHRASES = [
    "Все супер, легко і доступно.",
    "Дуже круто пояснює матеріал!",
    "Класний викладач, рекомендую.",
    "Все сподобалося, дякую за пару.",
]

NEGATIVE_REVIEW_PHRASES = [
    "Погано пояснив тему.",
    "Було нудно і не дуже зрозуміло.",
    "Хотілося б більше практики.",
    "Не сподобався підхід.",
]


@dataclass
class SeedStats:
    cities: int = 0
    disciplines: int = 0
    teachers: int = 0
    students: int = 0
    teacher_accounts: int = 0
    student_accounts: int = 0
    slots: int = 0
    bookings_active: int = 0
    bookings_completed: int = 0
    bookings_cancelled: int = 0
    reviews: int = 0


async def clear_database(session: AsyncSession) -> None:
    # Keep IDs stable between re-seeds to avoid stale filter references in UI.
    requested_tables = [
        "reviews",
        "bookings",
        "teacher_slots",
        "teacher_disciplines",
        "notifications",
        "students",
        "teachers",
        "user_accounts",
        "disciplines",
        "cities",
    ]

    existing_rows = await session.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """,
        ),
    )
    existing_tables = {row[0] for row in existing_rows}
    tables_to_truncate = [
        table_name for table_name in requested_tables if table_name in existing_tables
    ]

    if tables_to_truncate:
        truncate_sql = (
            "TRUNCATE TABLE "
            + ", ".join(tables_to_truncate)
            + " RESTART IDENTITY CASCADE"
        )
        await session.execute(text(truncate_sql))


def _pick_review_comment(rating: int) -> str:
    if rating >= 4:
        return random.choice(POSITIVE_REVIEW_PHRASES)
    return random.choice(NEGATIVE_REVIEW_PHRASES)


def _slot_window(
    now_utc: datetime,
    *,
    day_shift: int,
    hour: int,
    duration_hours: int = 1,
) -> tuple[datetime, datetime]:
    starts_at = (now_utc + timedelta(days=day_shift)).replace(
        hour=hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    ends_at = starts_at + timedelta(hours=duration_hours)
    return starts_at, ends_at


async def seed_database(session: AsyncSession) -> SeedStats:
    fake = Faker("uk_UA")
    fake.seed_instance(RANDOM_SEED)
    random.seed(RANDOM_SEED)

    stats = SeedStats()
    now_utc = datetime.now(timezone.utc)

    await clear_database(session)

    cities: list[City] = []
    for city_name in CITY_NAMES:
        city = City(name=city_name)
        session.add(city)
        cities.append(city)
    await session.flush()
    stats.cities = len(cities)

    disciplines: list[Discipline] = []
    for discipline_name in DISCIPLINE_NAMES:
        discipline = Discipline(name=discipline_name)
        session.add(discipline)
        disciplines.append(discipline)
    await session.flush()
    stats.disciplines = len(disciplines)

    admin_login = "admin"
    admin_password = "admin12345"
    admin_account = UserAccount(
        username=admin_login,
        email=f"{admin_login}@gmail.com",
        password_hash=hash_password(admin_password),
        role=UserRole.ADMIN,
    )
    session.add(admin_account)

    teachers: list[Teacher] = []
    for index in range(1, 9):
        teacher = Teacher(
            full_name=fake.name(),
            city_id=random.choice(cities).id,
        )
        session.add(teacher)
        teachers.append(teacher)
    await session.flush()
    stats.teachers = len(teachers)

    teacher_discipline_ids: dict[int, list[int]] = {}
    for teacher in teachers:
        assigned = random.sample(disciplines, k=random.randint(2, 3))
        teacher_discipline_ids[teacher.id] = [discipline.id for discipline in assigned]
        for discipline in assigned:
            session.add(
                TeacherDiscipline(
                    teacher_id=teacher.id,
                    discipline_id=discipline.id,
                ),
            )

    for index, teacher in enumerate(teachers, start=1):
        login = f"teacher_{index}"
        account = UserAccount(
            username=login,
            email=f"{login}@gmail.com",
            password_hash=hash_password(login),
            role=UserRole.TEACHER,
            teacher_id=teacher.id,
        )
        session.add(account)
    stats.teacher_accounts = len(teachers)

    students: list[Student] = []
    for index in range(1, 21):
        login = f"student_{index}"
        email = f"{login}@gmail.com"

        student = Student(
            full_name=fake.name(),
            email=email,
            city_id=random.choice(cities).id,
        )
        session.add(student)
        students.append(student)

    await session.flush()
    stats.students = len(students)

    for index, student in enumerate(students, start=1):
        login = f"student_{index}"
        account = UserAccount(
            username=login,
            email=f"{login}@gmail.com",
            password_hash=hash_password(login),
            role=UserRole.STUDENT,
            student_id=student.id,
        )
        session.add(account)
    stats.student_accounts = len(students)

    active_teachers = teachers[:6]

    for teacher_index, teacher in enumerate(active_teachers, start=1):
        discipline_ids = teacher_discipline_ids[teacher.id]

        completed_discipline_id = random.choice(discipline_ids)
        cancelled_discipline_id = random.choice(discipline_ids)
        active_discipline_id = random.choice(discipline_ids)
        future_free_discipline_id = random.choice(discipline_ids)

        completed_starts, completed_ends = _slot_window(
            now_utc,
            day_shift=-(18 + teacher_index),
            hour=10,
        )
        cancelled_starts, cancelled_ends = _slot_window(
            now_utc,
            day_shift=-(9 + teacher_index),
            hour=13,
        )
        active_starts, active_ends = _slot_window(
            now_utc,
            day_shift=3 + teacher_index,
            hour=11,
        )
        free_future_starts, free_future_ends = _slot_window(
            now_utc,
            day_shift=8 + teacher_index,
            hour=16,
        )

        completed_slot = TeacherSlot(
            teacher_id=teacher.id,
            discipline_id=completed_discipline_id,
            starts_at=completed_starts,
            ends_at=completed_ends,
            description="Завершене заняття для демонстрації відгуків.",
            capacity=4,
            is_active=False,
        )
        cancelled_slot = TeacherSlot(
            teacher_id=teacher.id,
            discipline_id=cancelled_discipline_id,
            starts_at=cancelled_starts,
            ends_at=cancelled_ends,
            description="Скасоване заняття для історії бронювань.",
            capacity=3,
            is_active=False,
        )
        active_slot = TeacherSlot(
            teacher_id=teacher.id,
            discipline_id=active_discipline_id,
            starts_at=active_starts,
            ends_at=active_ends,
            description="Майбутній активний слот.",
            capacity=5,
            is_active=True,
        )
        free_future_slot = TeacherSlot(
            teacher_id=teacher.id,
            discipline_id=future_free_discipline_id,
            starts_at=free_future_starts,
            ends_at=free_future_ends,
            description="Майбутній слот без записів для empty-state.",
            capacity=5,
            is_active=True,
        )

        session.add_all([completed_slot, cancelled_slot, active_slot, free_future_slot])
        await session.flush()
        stats.slots += 4

        teacher_students = random.sample(students, k=7)
        completed_students = teacher_students[:3]
        cancelled_students = teacher_students[3:5]
        active_students = teacher_students[5:7]

        for student in completed_students:
            booking = Booking(
                student_id=student.id,
                slot_id=completed_slot.id,
                status=BookingStatus.COMPLETED,
                created_at=completed_starts - timedelta(days=3),
            )
            session.add(booking)
            await session.flush()
            stats.bookings_completed += 1

            rating = random.randint(2, 5)
            review = Review(
                booking_id=booking.id,
                teacher_id=teacher.id,
                student_id=student.id,
                rating=rating,
                comment=_pick_review_comment(rating),
                created_at=completed_ends + timedelta(hours=2),
            )
            session.add(review)
            stats.reviews += 1

        for student in cancelled_students:
            booking = Booking(
                student_id=student.id,
                slot_id=cancelled_slot.id,
                status=BookingStatus.CANCELLED,
                created_at=cancelled_starts - timedelta(days=1),
            )
            session.add(booking)
            stats.bookings_cancelled += 1

        for student in active_students:
            booking = Booking(
                student_id=student.id,
                slot_id=active_slot.id,
                status=BookingStatus.ACTIVE,
                created_at=now_utc - timedelta(days=1),
            )
            session.add(booking)
            stats.bookings_active += 1

    await session.flush()
    return stats


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            stats = await seed_database(session)

    print("Seed completed successfully.")
    print(
        "Created: "
        f"cities={stats.cities}, "
        f"disciplines={stats.disciplines}, "
        f"teachers={stats.teachers}, "
        f"students={stats.students}, "
        f"teacher_accounts={stats.teacher_accounts}, "
        f"student_accounts={stats.student_accounts}, "
        f"slots={stats.slots}, "
        f"active_bookings={stats.bookings_active}, "
        f"completed_bookings={stats.bookings_completed}, "
        f"cancelled_bookings={stats.bookings_cancelled}, "
        f"reviews={stats.reviews}."
    )
    print("Teachers with no slots/bookings: teacher_7, teacher_8.")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())