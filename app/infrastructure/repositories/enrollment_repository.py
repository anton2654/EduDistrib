from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.dto.enrollment_dto import (
    CityCreateDTO,
    DisciplineCreateDTO,
    StudentCreateDTO,
    TeacherSlotUpdateDTO,
    TeacherCreateDTO,
    TeacherSlotCreateDTO,
)
from app.application.interfaces.enrollment_repository import (
    AnalyticsOverviewProjection,
    AvailableSlotProjection,
    BookingProjection,
    DisciplineAnalyticsProjection,
    EnrollmentRepositoryInterface,
    ReviewProjection,
    TeacherRatingSummary,
    TeacherSlotBookingProjection,
    TeacherAnalyticsProjection,
    TeacherSlotProjection,
)
from app.domain.entities.booking import Booking, BookingStatus
from app.domain.entities.city import City
from app.domain.entities.discipline import Discipline
from app.domain.entities.review import Review
from app.domain.entities.student import Student
from app.domain.entities.teacher import Teacher
from app.domain.entities.teacher_discipline import TeacherDiscipline
from app.domain.entities.teacher_slot import TeacherSlot


class EnrollmentRepository(EnrollmentRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_utilization_percent(reserved_seats: int, capacity_total: int) -> float:
        if capacity_total <= 0:
            return 0.0
        return round((reserved_seats / capacity_total) * 100, 2)

    @staticmethod
    def _build_slot_filter_conditions(
        city_id: int | None,
        discipline_id: int | None,
        teacher_id: int | None,
        starts_from: datetime | None,
        ends_to: datetime | None,
    ) -> list:
        conditions = []

        if city_id is not None:
            conditions.append(Teacher.city_id == city_id)
        if discipline_id is not None:
            conditions.append(TeacherSlot.discipline_id == discipline_id)
        if teacher_id is not None:
            conditions.append(TeacherSlot.teacher_id == teacher_id)
        if starts_from is not None:
            conditions.append(TeacherSlot.starts_at >= starts_from)
        if ends_to is not None:
            conditions.append(TeacherSlot.ends_at <= ends_to)

        return conditions

    async def create_city(self, city_in: CityCreateDTO) -> City:
        city = City(name=city_in.name)
        self._session.add(city)
        await self._session.commit()
        await self._session.refresh(city)
        return city

    async def list_cities(self) -> list[City]:
        stmt = select(City).order_by(City.name, City.id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_city_by_id(self, city_id: int) -> City | None:
        return await self._session.get(City, city_id)

    async def create_discipline(self, discipline_in: DisciplineCreateDTO) -> Discipline:
        discipline = Discipline(name=discipline_in.name)
        self._session.add(discipline)
        await self._session.commit()
        await self._session.refresh(discipline)
        return discipline

    async def list_disciplines(self) -> list[Discipline]:
        stmt = select(Discipline).order_by(Discipline.name, Discipline.id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_discipline_by_id(self, discipline_id: int) -> Discipline | None:
        return await self._session.get(Discipline, discipline_id)

    async def create_teacher(self, teacher_in: TeacherCreateDTO) -> Teacher:
        teacher = Teacher(
            full_name=teacher_in.full_name,
            city_id=teacher_in.city_id,
        )
        self._session.add(teacher)
        await self._session.commit()
        await self._session.refresh(teacher)
        return teacher

    async def list_teachers(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        search_query: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Teacher]:
        stmt = (
            select(Teacher)
            .options(selectinload(Teacher.discipline_links))
            .order_by(Teacher.full_name, Teacher.id)
        )

        if city_id is not None:
            stmt = stmt.where(Teacher.city_id == city_id)

        if discipline_id is not None:
            stmt = stmt.join(TeacherDiscipline).where(
                TeacherDiscipline.discipline_id == discipline_id,
            )

        if search_query is not None:
            stmt = stmt.where(Teacher.full_name.ilike(f"%{search_query}%"))

        stmt = stmt.offset(skip).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_teacher_rating_summaries(
        self,
        teacher_ids: list[int],
    ) -> dict[int, TeacherRatingSummary]:
        if not teacher_ids:
            return {}

        stmt = (
            select(
                Review.teacher_id,
                func.avg(Review.rating).label("average_rating"),
                func.count(Review.id).label("reviews_count"),
            )
            .where(Review.teacher_id.in_(teacher_ids))
            .group_by(Review.teacher_id)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return {
            row["teacher_id"]: TeacherRatingSummary(
                teacher_id=row["teacher_id"],
                average_rating=round(float(row["average_rating"]), 2),
                reviews_count=int(row["reviews_count"] or 0),
            )
            for row in rows
        }

    async def get_teacher_by_id(self, teacher_id: int) -> Teacher | None:
        stmt = (
            select(Teacher)
            .where(Teacher.id == teacher_id)
            .options(selectinload(Teacher.discipline_links))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def teacher_has_discipline(self, teacher_id: int, discipline_id: int) -> bool:
        stmt = select(TeacherDiscipline).where(
            TeacherDiscipline.teacher_id == teacher_id,
            TeacherDiscipline.discipline_id == discipline_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_student(self, student_in: StudentCreateDTO) -> Student:
        student = Student(
            full_name=student_in.full_name,
            email=student_in.email,
            city_id=student_in.city_id,
        )
        self._session.add(student)
        await self._session.commit()
        await self._session.refresh(student)
        return student

    async def list_students(
        self,
        city_id: int | None = None,
        email: str | None = None,
    ) -> list[Student]:
        stmt = select(Student).order_by(Student.full_name, Student.id)

        if city_id is not None:
            stmt = stmt.where(Student.city_id == city_id)

        if email is not None:
            stmt = stmt.where(Student.email == email)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_student_by_id(self, student_id: int) -> Student | None:
        return await self._session.get(Student, student_id)

    async def create_slot(self, slot_in: TeacherSlotCreateDTO) -> TeacherSlot:
        slot = TeacherSlot(**slot_in.model_dump())
        self._session.add(slot)
        await self._session.commit()
        await self._session.refresh(slot)
        return slot

    async def get_slot_by_id(self, slot_id: int) -> TeacherSlot | None:
        return await self._session.get(TeacherSlot, slot_id)

    async def list_teacher_slots(self, teacher_id: int) -> list[TeacherSlotProjection]:
        reserved_seats = func.coalesce(
            func.sum(case((Booking.status == BookingStatus.ACTIVE, 1), else_=0)),
            0,
        )

        stmt = (
            select(
                TeacherSlot.id.label("slot_id"),
                TeacherSlot.teacher_id,
                TeacherSlot.discipline_id,
                Discipline.name.label("discipline_name"),
                TeacherSlot.starts_at,
                TeacherSlot.ends_at,
                TeacherSlot.description,
                TeacherSlot.capacity,
                reserved_seats.label("reserved_seats"),
                TeacherSlot.is_active,
                TeacherSlot.created_at,
            )
            .join(Discipline, Discipline.id == TeacherSlot.discipline_id)
            .outerjoin(Booking, Booking.slot_id == TeacherSlot.id)
            .where(TeacherSlot.teacher_id == teacher_id)
            .group_by(
                TeacherSlot.id,
                TeacherSlot.teacher_id,
                TeacherSlot.discipline_id,
                Discipline.name,
                TeacherSlot.starts_at,
                TeacherSlot.ends_at,
                TeacherSlot.description,
                TeacherSlot.capacity,
                TeacherSlot.is_active,
                TeacherSlot.created_at,
            )
            .order_by(TeacherSlot.starts_at, TeacherSlot.id)
        )

        rows = (await self._session.execute(stmt)).mappings().all()
        return [
            TeacherSlotProjection(
                slot_id=row["slot_id"],
                teacher_id=row["teacher_id"],
                discipline_id=row["discipline_id"],
                discipline_name=row["discipline_name"],
                starts_at=row["starts_at"],
                ends_at=row["ends_at"],
                description=row["description"],
                capacity=row["capacity"],
                reserved_seats=int(row["reserved_seats"] or 0),
                is_active=row["is_active"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def update_slot(self, slot: TeacherSlot, slot_in: TeacherSlotUpdateDTO) -> TeacherSlot:
        for field, value in slot_in.model_dump(exclude_unset=True).items():
            setattr(slot, field, value)

        await self._session.commit()
        await self._session.refresh(slot)
        return slot

    async def delete_slot(self, slot: TeacherSlot) -> None:
        await self._session.execute(
            update(Booking)
            .where(Booking.slot_id == slot.id, Booking.status == BookingStatus.ACTIVE)
            .values(status=BookingStatus.CANCELLED)
        )

        slot.is_active = False
        await self._session.commit()

    async def list_available_slots(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AvailableSlotProjection]:
        reserved_seats = func.coalesce(
            func.sum(case((Booking.status == BookingStatus.ACTIVE, 1), else_=0)),
            0,
        )

        stmt = (
            select(
                TeacherSlot.id.label("slot_id"),
                Teacher.id.label("teacher_id"),
                Teacher.full_name.label("teacher_name"),
                City.id.label("city_id"),
                City.name.label("city_name"),
                Discipline.id.label("discipline_id"),
                Discipline.name.label("discipline_name"),
                TeacherSlot.starts_at,
                TeacherSlot.ends_at,
                TeacherSlot.description,
                TeacherSlot.capacity,
                reserved_seats.label("reserved_seats"),
            )
            .join(Teacher, Teacher.id == TeacherSlot.teacher_id)
            .join(City, City.id == Teacher.city_id)
            .join(Discipline, Discipline.id == TeacherSlot.discipline_id)
            .outerjoin(Booking, Booking.slot_id == TeacherSlot.id)
            .where(TeacherSlot.is_active.is_(True))
            .group_by(
                TeacherSlot.id,
                Teacher.id,
                Teacher.full_name,
                City.id,
                City.name,
                Discipline.id,
                Discipline.name,
                TeacherSlot.starts_at,
                TeacherSlot.ends_at,
                TeacherSlot.description,
                TeacherSlot.capacity,
            )
            .having(reserved_seats < TeacherSlot.capacity)
            .order_by(TeacherSlot.starts_at, TeacherSlot.id)
        )

        if city_id is not None:
            stmt = stmt.where(City.id == city_id)

        if discipline_id is not None:
            stmt = stmt.where(Discipline.id == discipline_id)

        if teacher_id is not None:
            stmt = stmt.where(Teacher.id == teacher_id)

        stmt = stmt.offset(skip).limit(limit)

        rows = (await self._session.execute(stmt)).mappings().all()

        return [
            AvailableSlotProjection(
                slot_id=row["slot_id"],
                teacher_id=row["teacher_id"],
                teacher_name=row["teacher_name"],
                city_id=row["city_id"],
                city_name=row["city_name"],
                discipline_id=row["discipline_id"],
                discipline_name=row["discipline_name"],
                starts_at=row["starts_at"],
                ends_at=row["ends_at"],
                description=row["description"],
                capacity=row["capacity"],
                reserved_seats=int(row["reserved_seats"] or 0),
            )
            for row in rows
        ]

    async def get_overview_analytics(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
        starts_from: datetime | None = None,
        ends_to: datetime | None = None,
    ) -> AnalyticsOverviewProjection:
        total_cities = int((await self._session.execute(select(func.count(City.id)))).scalar_one() or 0)
        total_disciplines = int(
            (await self._session.execute(select(func.count(Discipline.id)))).scalar_one() or 0,
        )
        total_teachers = int((await self._session.execute(select(func.count(Teacher.id)))).scalar_one() or 0)
        total_students = int((await self._session.execute(select(func.count(Student.id)))).scalar_one() or 0)

        conditions = self._build_slot_filter_conditions(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )

        slot_stats_stmt = (
            select(
                TeacherSlot.id.label("slot_id"),
                TeacherSlot.is_active.label("is_active"),
                TeacherSlot.capacity.label("capacity"),
                func.coalesce(
                    func.sum(case((Booking.status == BookingStatus.ACTIVE, 1), else_=0)),
                    0,
                ).label("reserved_seats"),
            )
            .join(Teacher, Teacher.id == TeacherSlot.teacher_id)
            .outerjoin(Booking, Booking.slot_id == TeacherSlot.id)
            .group_by(TeacherSlot.id, TeacherSlot.is_active, TeacherSlot.capacity)
        )
        if conditions:
            slot_stats_stmt = slot_stats_stmt.where(*conditions)

        slot_stats_subquery = slot_stats_stmt.subquery()

        overview_stmt = select(
            func.count(slot_stats_subquery.c.slot_id).label("slots_total"),
            func.coalesce(
                func.sum(
                    case((slot_stats_subquery.c.is_active.is_(True), 1), else_=0),
                ),
                0,
            ).label("slots_active"),
            func.coalesce(func.sum(slot_stats_subquery.c.reserved_seats), 0).label("bookings_total"),
            func.coalesce(func.sum(slot_stats_subquery.c.capacity), 0).label("capacity_total"),
        )
        overview_row = (await self._session.execute(overview_stmt)).mappings().one()

        filtered_slots_total = int(overview_row["slots_total"] or 0)
        filtered_slots_active = int(overview_row["slots_active"] or 0)
        filtered_bookings_total = int(overview_row["bookings_total"] or 0)
        filtered_capacity_total = int(overview_row["capacity_total"] or 0)
        filtered_reserved_seats_total = filtered_bookings_total

        return AnalyticsOverviewProjection(
            total_cities=total_cities,
            total_disciplines=total_disciplines,
            total_teachers=total_teachers,
            total_students=total_students,
            filtered_slots_total=filtered_slots_total,
            filtered_slots_active=filtered_slots_active,
            filtered_bookings_total=filtered_bookings_total,
            filtered_capacity_total=filtered_capacity_total,
            filtered_reserved_seats_total=filtered_reserved_seats_total,
            utilization_rate_percent=self._to_utilization_percent(
                filtered_reserved_seats_total,
                filtered_capacity_total,
            ),
        )

    async def list_teacher_analytics(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
        starts_from: datetime | None = None,
        ends_to: datetime | None = None,
    ) -> list[TeacherAnalyticsProjection]:
        conditions = self._build_slot_filter_conditions(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )

        slot_stats_stmt = (
            select(
                Teacher.id.label("teacher_id"),
                Teacher.full_name.label("teacher_name"),
                City.id.label("city_id"),
                City.name.label("city_name"),
                TeacherSlot.id.label("slot_id"),
                TeacherSlot.is_active.label("is_active"),
                TeacherSlot.capacity.label("capacity"),
                func.coalesce(
                    func.sum(case((Booking.status == BookingStatus.ACTIVE, 1), else_=0)),
                    0,
                ).label("reserved_seats"),
            )
            .join(Teacher, Teacher.id == TeacherSlot.teacher_id)
            .join(City, City.id == Teacher.city_id)
            .outerjoin(Booking, Booking.slot_id == TeacherSlot.id)
            .group_by(
                Teacher.id,
                Teacher.full_name,
                City.id,
                City.name,
                TeacherSlot.id,
                TeacherSlot.is_active,
                TeacherSlot.capacity,
            )
        )
        if conditions:
            slot_stats_stmt = slot_stats_stmt.where(*conditions)

        slot_stats_subquery = slot_stats_stmt.subquery()

        teacher_aggregate_stmt = (
            select(
                slot_stats_subquery.c.teacher_id,
                slot_stats_subquery.c.teacher_name,
                slot_stats_subquery.c.city_id,
                slot_stats_subquery.c.city_name,
                func.count(slot_stats_subquery.c.slot_id).label("slots_total"),
                func.coalesce(
                    func.sum(
                        case((slot_stats_subquery.c.is_active.is_(True), 1), else_=0),
                    ),
                    0,
                ).label("slots_active"),
                func.coalesce(func.sum(slot_stats_subquery.c.reserved_seats), 0).label("bookings_total"),
                func.coalesce(func.sum(slot_stats_subquery.c.capacity), 0).label("capacity_total"),
            )
            .group_by(
                slot_stats_subquery.c.teacher_id,
                slot_stats_subquery.c.teacher_name,
                slot_stats_subquery.c.city_id,
                slot_stats_subquery.c.city_name,
            )
            .order_by(
                func.coalesce(func.sum(slot_stats_subquery.c.reserved_seats), 0).desc(),
                slot_stats_subquery.c.teacher_name,
            )
        )

        rows = (await self._session.execute(teacher_aggregate_stmt)).mappings().all()
        return [
            TeacherAnalyticsProjection(
                teacher_id=row["teacher_id"],
                teacher_name=row["teacher_name"],
                city_id=row["city_id"],
                city_name=row["city_name"],
                slots_total=int(row["slots_total"] or 0),
                slots_active=int(row["slots_active"] or 0),
                bookings_total=int(row["bookings_total"] or 0),
                capacity_total=int(row["capacity_total"] or 0),
                reserved_seats_total=int(row["bookings_total"] or 0),
                utilization_rate_percent=self._to_utilization_percent(
                    int(row["bookings_total"] or 0),
                    int(row["capacity_total"] or 0),
                ),
            )
            for row in rows
        ]

    async def list_discipline_analytics(
        self,
        city_id: int | None = None,
        discipline_id: int | None = None,
        teacher_id: int | None = None,
        starts_from: datetime | None = None,
        ends_to: datetime | None = None,
    ) -> list[DisciplineAnalyticsProjection]:
        conditions = self._build_slot_filter_conditions(
            city_id=city_id,
            discipline_id=discipline_id,
            teacher_id=teacher_id,
            starts_from=starts_from,
            ends_to=ends_to,
        )

        slot_stats_stmt = (
            select(
                Discipline.id.label("discipline_id"),
                Discipline.name.label("discipline_name"),
                TeacherSlot.id.label("slot_id"),
                TeacherSlot.is_active.label("is_active"),
                TeacherSlot.capacity.label("capacity"),
                func.coalesce(
                    func.sum(case((Booking.status == BookingStatus.ACTIVE, 1), else_=0)),
                    0,
                ).label("reserved_seats"),
            )
            .join(Teacher, Teacher.id == TeacherSlot.teacher_id)
            .join(Discipline, Discipline.id == TeacherSlot.discipline_id)
            .outerjoin(Booking, Booking.slot_id == TeacherSlot.id)
            .group_by(
                Discipline.id,
                Discipline.name,
                TeacherSlot.id,
                TeacherSlot.is_active,
                TeacherSlot.capacity,
            )
        )
        if conditions:
            slot_stats_stmt = slot_stats_stmt.where(*conditions)

        slot_stats_subquery = slot_stats_stmt.subquery()

        discipline_aggregate_stmt = (
            select(
                slot_stats_subquery.c.discipline_id,
                slot_stats_subquery.c.discipline_name,
                func.count(slot_stats_subquery.c.slot_id).label("slots_total"),
                func.coalesce(
                    func.sum(
                        case((slot_stats_subquery.c.is_active.is_(True), 1), else_=0),
                    ),
                    0,
                ).label("slots_active"),
                func.coalesce(func.sum(slot_stats_subquery.c.reserved_seats), 0).label("bookings_total"),
                func.coalesce(func.sum(slot_stats_subquery.c.capacity), 0).label("capacity_total"),
            )
            .group_by(
                slot_stats_subquery.c.discipline_id,
                slot_stats_subquery.c.discipline_name,
            )
            .order_by(
                func.coalesce(func.sum(slot_stats_subquery.c.reserved_seats), 0).desc(),
                slot_stats_subquery.c.discipline_name,
            )
        )

        rows = (await self._session.execute(discipline_aggregate_stmt)).mappings().all()
        return [
            DisciplineAnalyticsProjection(
                discipline_id=row["discipline_id"],
                discipline_name=row["discipline_name"],
                slots_total=int(row["slots_total"] or 0),
                slots_active=int(row["slots_active"] or 0),
                bookings_total=int(row["bookings_total"] or 0),
                capacity_total=int(row["capacity_total"] or 0),
                reserved_seats_total=int(row["bookings_total"] or 0),
                utilization_rate_percent=self._to_utilization_percent(
                    int(row["bookings_total"] or 0),
                    int(row["capacity_total"] or 0),
                ),
            )
            for row in rows
        ]

    async def count_slot_bookings(self, slot_id: int) -> int:
        stmt = select(func.count(Booking.id)).where(
            Booking.slot_id == slot_id,
            Booking.status == BookingStatus.ACTIVE,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def has_active_booking(self, student_id: int, slot_id: int) -> bool:
        stmt = select(Booking.id).where(
            Booking.student_id == student_id,
            Booking.slot_id == slot_id,
            Booking.status == BookingStatus.ACTIVE,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def student_has_time_conflict(
        self,
        student_id: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> bool:
        stmt = (
            select(Booking.id)
            .join(TeacherSlot, TeacherSlot.id == Booking.slot_id)
            .where(
                Booking.student_id == student_id,
                Booking.status == BookingStatus.ACTIVE,
                TeacherSlot.starts_at < ends_at,
                TeacherSlot.ends_at > starts_at,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_booking(self, student_id: int, slot_id: int) -> Booking:
        booking = Booking(
            student_id=student_id,
            slot_id=slot_id,
            status=BookingStatus.ACTIVE,
        )
        self._session.add(booking)
        await self._session.commit()
        await self._session.refresh(booking)
        return booking

    async def list_bookings(
        self,
        student_id: int | None = None,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[BookingProjection]:
        stmt = (
            select(
                Booking.id.label("booking_id"),
                Student.id.label("student_id"),
                Student.full_name.label("student_name"),
                Student.email.label("student_email"),
                TeacherSlot.id.label("slot_id"),
                Teacher.id.label("teacher_id"),
                Teacher.full_name.label("teacher_name"),
                City.id.label("city_id"),
                City.name.label("city_name"),
                Discipline.id.label("discipline_id"),
                Discipline.name.label("discipline_name"),
                TeacherSlot.starts_at,
                TeacherSlot.ends_at,
                TeacherSlot.description,
                Booking.status,
                case((Review.id.is_not(None), True), else_=False).label("has_review"),
                Booking.created_at,
            )
            .join(Student, Student.id == Booking.student_id)
            .join(TeacherSlot, TeacherSlot.id == Booking.slot_id)
            .join(Teacher, Teacher.id == TeacherSlot.teacher_id)
            .join(City, City.id == Teacher.city_id)
            .join(Discipline, Discipline.id == TeacherSlot.discipline_id)
            .outerjoin(
                Review,
                Review.booking_id == Booking.id,
            )
            .order_by(TeacherSlot.starts_at, Booking.id)
        )

        if student_id is not None:
            stmt = stmt.where(Student.id == student_id)

        if status is not None:
            stmt = stmt.where(Booking.status == status)

        stmt = stmt.offset(skip).limit(limit)

        rows = (await self._session.execute(stmt)).mappings().all()

        return [
            BookingProjection(
                booking_id=row["booking_id"],
                student_id=row["student_id"],
                student_name=row["student_name"],
                student_email=row["student_email"],
                slot_id=row["slot_id"],
                teacher_id=row["teacher_id"],
                teacher_name=row["teacher_name"],
                city_id=row["city_id"],
                city_name=row["city_name"],
                discipline_id=row["discipline_id"],
                discipline_name=row["discipline_name"],
                starts_at=row["starts_at"],
                ends_at=row["ends_at"],
                description=row["description"],
                status=row["status"],
                has_review=bool(row["has_review"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def list_teacher_slot_bookings(
        self,
        slot_id: int,
        status: BookingStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TeacherSlotBookingProjection]:
        stmt = (
            select(
                Booking.id.label("booking_id"),
                Student.id.label("student_id"),
                Student.full_name.label("student_name"),
                Student.email.label("student_email"),
                Booking.status,
                Booking.created_at,
            )
            .join(Student, Student.id == Booking.student_id)
            .where(Booking.slot_id == slot_id)
            .order_by(Booking.created_at, Booking.id)
            .offset(skip)
            .limit(limit)
        )

        if status is not None:
            stmt = stmt.where(Booking.status == status)

        rows = (await self._session.execute(stmt)).mappings().all()
        return [
            TeacherSlotBookingProjection(
                booking_id=row["booking_id"],
                student_id=row["student_id"],
                student_name=row["student_name"],
                student_email=row["student_email"],
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def get_booking_by_id(self, booking_id: int) -> Booking | None:
        return await self._session.get(Booking, booking_id)

    async def cancel_active_bookings_for_slot(self, slot_id: int) -> int:
        stmt = (
            update(Booking)
            .where(
                Booking.slot_id == slot_id,
                Booking.status == BookingStatus.ACTIVE,
            )
            .values(status=BookingStatus.CANCELLED)
            .returning(Booking.id)
        )
        result = await self._session.execute(stmt)
        updated_ids = result.scalars().all()
        await self._session.commit()
        return len(updated_ids)

    async def complete_active_bookings_for_slot(self, slot_id: int) -> int:
        stmt = (
            update(Booking)
            .where(
                Booking.slot_id == slot_id,
                Booking.status == BookingStatus.ACTIVE,
            )
            .values(status=BookingStatus.COMPLETED)
            .returning(Booking.id)
        )
        result = await self._session.execute(stmt)
        updated_ids = result.scalars().all()
        await self._session.commit()
        return len(updated_ids)

    async def get_review_by_booking(self, booking_id: int) -> Review | None:
        stmt = select(Review).where(Review.booking_id == booking_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_review(
        self,
        *,
        booking_id: int,
        teacher_id: int,
        student_id: int,
        rating: int,
        comment: str | None,
    ) -> Review:
        review = Review(
            booking_id=booking_id,
            teacher_id=teacher_id,
            student_id=student_id,
            rating=rating,
            comment=comment,
        )
        self._session.add(review)
        await self._session.commit()
        await self._session.refresh(review)
        return review

    async def list_reviews(
        self,
        teacher_id: int | None = None,
        discipline_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ReviewProjection]:
        stmt = (
            select(
                Review.id.label("review_id"),
                Review.booking_id,
                Review.teacher_id,
                Teacher.full_name.label("teacher_name"),
                Review.student_id,
                Student.full_name.label("student_name"),
                Discipline.id.label("discipline_id"),
                Discipline.name.label("discipline_name"),
                Review.rating,
                Review.comment,
                Review.created_at,
            )
            .join(Teacher, Teacher.id == Review.teacher_id)
            .join(Student, Student.id == Review.student_id)
            .join(Booking, Booking.id == Review.booking_id)
            .join(TeacherSlot, TeacherSlot.id == Booking.slot_id)
            .join(Discipline, Discipline.id == TeacherSlot.discipline_id)
            .order_by(Review.created_at.desc(), Review.id.desc())
            .offset(skip)
            .limit(limit)
        )

        if teacher_id is not None:
            stmt = stmt.where(Review.teacher_id == teacher_id)

        if discipline_id is not None:
            stmt = stmt.where(TeacherSlot.discipline_id == discipline_id)

        rows = (await self._session.execute(stmt)).mappings().all()
        return [
            ReviewProjection(
                review_id=row["review_id"],
                booking_id=row["booking_id"],
                teacher_id=row["teacher_id"],
                teacher_name=row["teacher_name"],
                student_id=row["student_id"],
                student_name=row["student_name"],
                discipline_id=row["discipline_id"],
                discipline_name=row["discipline_name"],
                rating=row["rating"],
                comment=row["comment"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def update_booking_status(self, booking: Booking, status: BookingStatus) -> Booking:
        booking.status = status
        await self._session.commit()
        await self._session.refresh(booking)
        return booking

    async def delete_booking(self, booking: Booking) -> None:
        await self._session.delete(booking)
        await self._session.commit()
