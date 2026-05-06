"""Seed Ukrainian demo dataset.

Revision ID: 20260503_0010
Revises: 20260503_0009
Create Date: 2026-05-03 14:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from alembic import op
from faker import Faker

from app.core.security import hash_password


revision: str = "20260503_0010"
down_revision: str | None = "20260503_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CITIES = [
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

DISCIPLINES = [
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

REVIEW_COMMENTS = {
    5: [
        "Все супер, легко і доступно.",
        "Дуже зрозуміле пояснення, заняття сподобалось.",
        "Викладач добре пояснив тему, було цікаво.",
        "Матеріал подано просто і без зайвого.",
    ],
    4: [
        "Загалом добре, тему зрозумів.",
        "Пояснення хороше, але хотілося більше прикладів.",
        "Було корисно і спокійно.",
        "Нормальне заняття, основне стало зрозуміло.",
    ],
    3: [
        "Частину теми зрозумів, але треба ще повторити.",
        "Було нормально, але місцями складно.",
        "Пояснення непогане, але темп зависокий.",
    ],
    2: [
        "Погано пояснив тему, було важко зрозуміти.",
        "Мало прикладів, тема залишилась не дуже ясною.",
        "Очікував простіше пояснення.",
    ],
}


def _scalar_id(connection: sa.Connection, query: sa.sql.ClauseElement, params: dict) -> int:
    value = connection.execute(query, params).scalar_one()
    return int(value)


def _cleanup_existing_demo_data(connection: sa.Connection) -> None:
    connection.execute(sa.text("DELETE FROM notifications"))
    connection.execute(sa.text("DELETE FROM reviews"))
    connection.execute(sa.text("DELETE FROM bookings"))
    connection.execute(sa.text("DELETE FROM teacher_slots"))
    connection.execute(sa.text("DELETE FROM teacher_disciplines"))
    connection.execute(sa.text("DELETE FROM tasks"))
    connection.execute(sa.text("DELETE FROM user_accounts WHERE role <> 'admin'"))
    connection.execute(sa.text("DELETE FROM teachers"))
    connection.execute(sa.text("DELETE FROM students"))
    connection.execute(sa.text("DELETE FROM disciplines"))
    connection.execute(sa.text("DELETE FROM cities"))


def _ensure_admin_account(connection: sa.Connection) -> None:
    admin_exists = connection.execute(
        sa.text("SELECT 1 FROM user_accounts WHERE role = 'admin' LIMIT 1"),
    ).scalar_one_or_none()
    if admin_exists is not None:
        return

    connection.execute(
        sa.text(
            """
            INSERT INTO user_accounts (username, email, password_hash, role)
            VALUES (:username, :email, :password_hash, 'admin')
            """,
        ),
        {
            "username": "admin",
            "email": "admin@gmail.com",
            "password_hash": hash_password("admin12345"),
        },
    )


def _insert_reference_data(connection: sa.Connection) -> tuple[dict[str, int], dict[str, int]]:
    city_ids: dict[str, int] = {}
    discipline_ids: dict[str, int] = {}

    for name in CITIES:
        city_ids[name] = _scalar_id(
            connection,
            sa.text("INSERT INTO cities (name) VALUES (:name) RETURNING id"),
            {"name": name},
        )

    for name in DISCIPLINES:
        discipline_ids[name] = _scalar_id(
            connection,
            sa.text("INSERT INTO disciplines (name) VALUES (:name) RETURNING id"),
            {"name": name},
        )

    return city_ids, discipline_ids


def _insert_users(
    connection: sa.Connection,
    faker: Faker,
    city_ids: dict[str, int],
) -> tuple[dict[str, int], dict[str, int]]:
    teacher_ids: dict[str, int] = {}
    student_ids: dict[str, int] = {}

    teacher_city_cycle = [
        "Київ",
        "Харків",
        "Одеса",
        "Дніпро",
        "Львів",
        "Полтава",
        "Чернігів",
        "Тернопіль",
    ]
    for number in range(1, 9):
        username = f"teacher_{number}"
        teacher_id = _scalar_id(
            connection,
            sa.text(
                """
                INSERT INTO teachers (full_name, city_id)
                VALUES (:full_name, :city_id)
                RETURNING id
                """,
            ),
            {
                "full_name": faker.name(),
                "city_id": city_ids[teacher_city_cycle[number - 1]],
            },
        )
        teacher_ids[username] = teacher_id
        connection.execute(
            sa.text(
                """
                INSERT INTO user_accounts (username, email, password_hash, role, teacher_id)
                VALUES (:username, :email, :password_hash, 'teacher', :teacher_id)
                """,
            ),
            {
                "username": username,
                "email": f"{username}@gmail.com",
                "password_hash": hash_password(username),
                "teacher_id": teacher_id,
            },
        )

    for number in range(1, 21):
        username = f"student_{number}"
        student_id = _scalar_id(
            connection,
            sa.text(
                """
                INSERT INTO students (full_name, email, city_id)
                VALUES (:full_name, :email, :city_id)
                RETURNING id
                """,
            ),
            {
                "full_name": faker.name(),
                "email": f"{username}@gmail.com",
                "city_id": city_ids[CITIES[(number - 1) % len(CITIES)]],
            },
        )
        student_ids[username] = student_id
        connection.execute(
            sa.text(
                """
                INSERT INTO user_accounts (username, email, password_hash, role, student_id)
                VALUES (:username, :email, :password_hash, 'student', :student_id)
                """,
            ),
            {
                "username": username,
                "email": f"{username}@gmail.com",
                "password_hash": hash_password(username),
                "student_id": student_id,
            },
        )

    return teacher_ids, student_ids


def _assign_disciplines(
    connection: sa.Connection,
    teacher_ids: dict[str, int],
    discipline_ids: dict[str, int],
) -> None:
    teacher_disciplines = {
        "teacher_1": ["Математика", "Фізика"],
        "teacher_2": ["Англійська", "Німецька"],
        "teacher_3": ["Програмування", "Математика"],
        "teacher_4": ["Англійська", "Французька"],
        "teacher_5": ["Біологія", "Хімія"],
        "teacher_6": ["Географія", "Українська мова"],
        "teacher_7": ["Фізика", "Зарубіжна література"],
        "teacher_8": ["Українська література", "Програмування"],
    }

    for teacher_username, discipline_names in teacher_disciplines.items():
        for discipline_name in discipline_names:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO teacher_disciplines (teacher_id, discipline_id)
                    VALUES (:teacher_id, :discipline_id)
                    """,
                ),
                {
                    "teacher_id": teacher_ids[teacher_username],
                    "discipline_id": discipline_ids[discipline_name],
                },
            )


def _insert_slot(
    connection: sa.Connection,
    *,
    teacher_id: int,
    discipline_id: int,
    starts_at: datetime,
    ends_at: datetime,
    address: str,
    capacity: int,
    is_active: bool,
    completed_at: datetime | None = None,
    description: str | None = None,
) -> int:
    return _scalar_id(
        connection,
        sa.text(
            """
            INSERT INTO teacher_slots (
                teacher_id, discipline_id, starts_at, ends_at, description,
                address, capacity, is_active, completed_at
            )
            VALUES (
                :teacher_id, :discipline_id, :starts_at, :ends_at, :description,
                :address, :capacity, :is_active, :completed_at
            )
            RETURNING id
            """,
        ),
        {
            "teacher_id": teacher_id,
            "discipline_id": discipline_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "description": description,
            "address": address,
            "capacity": capacity,
            "is_active": is_active,
            "completed_at": completed_at,
        },
    )


def _insert_booking(
    connection: sa.Connection,
    *,
    student_id: int,
    slot_id: int,
    status: str,
    created_at: datetime,
) -> int:
    return _scalar_id(
        connection,
        sa.text(
            """
            INSERT INTO bookings (student_id, slot_id, status, created_at)
            VALUES (:student_id, :slot_id, :status, :created_at)
            RETURNING id
            """,
        ),
        {
            "student_id": student_id,
            "slot_id": slot_id,
            "status": status,
            "created_at": created_at,
        },
    )


def _insert_review(
    connection: sa.Connection,
    *,
    booking_id: int,
    teacher_id: int,
    student_id: int,
    rating: int,
    comment: str,
    created_at: datetime,
) -> None:
    connection.execute(
        sa.text(
            """
            INSERT INTO reviews (booking_id, teacher_id, student_id, rating, comment, created_at)
            VALUES (:booking_id, :teacher_id, :student_id, :rating, :comment, :created_at)
            """,
        ),
        {
            "booking_id": booking_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "rating": rating,
            "comment": comment,
            "created_at": created_at,
        },
    )


def _seed_slots_bookings_and_reviews(
    connection: sa.Connection,
    faker: Faker,
    teacher_ids: dict[str, int],
    student_ids: dict[str, int],
    discipline_ids: dict[str, int],
) -> None:
    now = datetime.now(timezone.utc)
    student_usernames = list(student_ids)
    teacher_slot_specs = [
        ("teacher_3", "Програмування", "вул. Хрещатик, 12", 0),
        ("teacher_4", "Англійська", "вул. Сумська, 44", 3),
        ("teacher_5", "Біологія", "вул. Дерибасівська, 7", 6),
        ("teacher_6", "Географія", "просп. Дмитра Яворницького, 21", 9),
        ("teacher_7", "Фізика", "вул. Соборна, 15", 12),
        ("teacher_8", "Українська література", "вул. Руська, 3", 15),
    ]

    for index, (teacher_username, discipline_name, address, student_offset) in enumerate(teacher_slot_specs):
        teacher_id = teacher_ids[teacher_username]
        discipline_id = discipline_ids[discipline_name]
        duration = timedelta(minutes=90)
        past_start = now - timedelta(days=10 - index, hours=2)
        cancelled_start = now - timedelta(days=3 + index, hours=1)
        future_start = now + timedelta(days=2 + index, hours=9 + index)

        completed_slot_id = _insert_slot(
            connection,
            teacher_id=teacher_id,
            discipline_id=discipline_id,
            starts_at=past_start,
            ends_at=past_start + duration,
            address=address,
            capacity=3,
            is_active=False,
            completed_at=past_start + duration,
            description="Практичне заняття з розбором теми.",
        )
        cancelled_slot_id = _insert_slot(
            connection,
            teacher_id=teacher_id,
            discipline_id=discipline_id,
            starts_at=cancelled_start,
            ends_at=cancelled_start + duration,
            address=address,
            capacity=2,
            is_active=False,
            description="Заняття було скасовано викладачем.",
        )
        active_slot_id = _insert_slot(
            connection,
            teacher_id=teacher_id,
            discipline_id=discipline_id,
            starts_at=future_start,
            ends_at=future_start + duration,
            address=address,
            capacity=4,
            is_active=True,
            description="Планове групове заняття.",
        )

        completed_students = [
            student_usernames[(student_offset + offset) % len(student_usernames)]
            for offset in range(2)
        ]
        for offset, student_username in enumerate(completed_students):
            student_id = student_ids[student_username]
            booking_id = _insert_booking(
                connection,
                student_id=student_id,
                slot_id=completed_slot_id,
                status="completed",
                created_at=past_start - timedelta(days=5, hours=offset),
            )
            rating = [5, 4, 3, 2, 5, 4, 5, 3, 4, 5, 2, 4][index * 2 + offset]
            comment_options = REVIEW_COMMENTS[rating]
            _insert_review(
                connection,
                booking_id=booking_id,
                teacher_id=teacher_id,
                student_id=student_id,
                rating=rating,
                comment=str(faker.random_element(elements=comment_options)),
                created_at=past_start + duration + timedelta(hours=offset + 1),
            )

        cancelled_student_id = student_ids[student_usernames[(student_offset + 2) % len(student_usernames)]]
        _insert_booking(
            connection,
            student_id=cancelled_student_id,
            slot_id=cancelled_slot_id,
            status="cancelled",
            created_at=cancelled_start - timedelta(days=2),
        )

        for offset in range(2):
            active_student_id = student_ids[student_usernames[(student_offset + 3 + offset) % len(student_usernames)]]
            _insert_booking(
                connection,
                student_id=active_student_id,
                slot_id=active_slot_id,
                status="active",
                created_at=now - timedelta(hours=index + offset + 1),
            )


def upgrade() -> None:
    connection = op.get_bind()
    faker = Faker("uk_UA")
    Faker.seed(20260503)

    _cleanup_existing_demo_data(connection)
    _ensure_admin_account(connection)
    city_ids, discipline_ids = _insert_reference_data(connection)
    teacher_ids, student_ids = _insert_users(connection, faker, city_ids)
    _assign_disciplines(connection, teacher_ids, discipline_ids)
    _seed_slots_bookings_and_reviews(connection, faker, teacher_ids, student_ids, discipline_ids)


def downgrade() -> None:
    connection = op.get_bind()
    _cleanup_existing_demo_data(connection)
