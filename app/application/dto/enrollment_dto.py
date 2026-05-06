from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator, model_validator

from app.application.dto.email_validation import (
    ensure_not_common_email_typo,
    normalize_email_input,
)
from app.domain.entities.booking import BookingStatus


class LessonDisplayStatus(str, Enum):
    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def _to_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def resolve_time_based_display_status(
    starts_at: datetime,
    ends_at: datetime,
    now: datetime | None = None,
) -> LessonDisplayStatus:
    current = now or datetime.now(timezone.utc)
    starts_at_utc = _to_aware_utc(starts_at)
    ends_at_utc = _to_aware_utc(ends_at)

    if current < starts_at_utc:
        return LessonDisplayStatus.UPCOMING
    if current < ends_at_utc:
        return LessonDisplayStatus.IN_PROGRESS
    return LessonDisplayStatus.COMPLETED


def resolve_slot_display_status(
    is_active: bool,
    starts_at: datetime,
    ends_at: datetime,
    completed_at: datetime | None = None,
    now: datetime | None = None,
) -> LessonDisplayStatus:
    if completed_at is not None:
        return LessonDisplayStatus.COMPLETED

    if is_active:
        return resolve_time_based_display_status(starts_at, ends_at, now)

    current = now or datetime.now(timezone.utc)
    if current < _to_aware_utc(ends_at):
        return LessonDisplayStatus.CANCELLED
    return LessonDisplayStatus.COMPLETED


def resolve_booking_display_status(
    status: BookingStatus,
    starts_at: datetime,
    ends_at: datetime,
    now: datetime | None = None,
) -> LessonDisplayStatus:
    if status == BookingStatus.CANCELLED:
        return LessonDisplayStatus.CANCELLED
    if status == BookingStatus.COMPLETED:
        return LessonDisplayStatus.COMPLETED

    time_based_status = resolve_time_based_display_status(starts_at, ends_at, now)
    if time_based_status == LessonDisplayStatus.COMPLETED:
        return LessonDisplayStatus.ACTIVE
    return time_based_status


class CityCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class CityReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class DisciplineCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class DisciplineReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TeacherCreateDTO(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    city_id: int = Field(gt=0)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        return value.strip()


class TeacherReadDTO(BaseModel):
    id: int
    full_name: str
    city_id: int
    discipline_ids: list[int]
    average_rating: float | None = None
    reviews_count: int = 0


class StudentCreateDTO(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=255)
    city_id: int = Field(gt=0)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = normalize_email_input(value)
        if normalized is None:
            raise ValueError("email cannot be blank")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email_domain_typo(cls, value: EmailStr) -> EmailStr:
        validated = ensure_not_common_email_typo(value)
        if validated is None:
            raise ValueError("email cannot be blank")
        return validated


class StudentReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    city_id: int


class TeacherSlotCreateDTO(BaseModel):
    teacher_id: int = Field(gt=0)
    discipline_id: int = Field(gt=0)
    starts_at: datetime
    ends_at: datetime
    description: str | None = None
    address: str | None = None
    capacity: int = Field(default=1, gt=0)
    is_active: bool = True

    @field_validator("description", "address")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_time_range(self) -> "TeacherSlotCreateDTO":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class TeacherSlotManageCreateDTO(BaseModel):
    discipline_id: int = Field(gt=0)
    starts_at: datetime
    ends_at: datetime
    description: str | None = None
    address: str | None = None
    capacity: int = Field(default=1, gt=0)
    is_active: bool = True

    @field_validator("description", "address")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_time_range(self) -> "TeacherSlotManageCreateDTO":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class TeacherSlotUpdateDTO(BaseModel):
    discipline_id: int | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    description: str | None = None
    address: str | None = None
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("description", "address")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_update_payload(self) -> "TeacherSlotUpdateDTO":
        has_any_field = bool(self.model_fields_set)
        if not has_any_field:
            raise ValueError("At least one field must be provided for slot update")

        if self.starts_at is not None and self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")

        return self


class TeacherSlotReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    discipline_id: int
    starts_at: datetime
    ends_at: datetime
    description: str | None
    address: str | None = None
    capacity: int
    is_active: bool
    completed_at: datetime | None = None
    created_at: datetime

    @computed_field
    @property
    def display_status(self) -> LessonDisplayStatus:
        return resolve_slot_display_status(self.is_active, self.starts_at, self.ends_at, self.completed_at)


class TeacherSlotDetailsReadDTO(BaseModel):
    slot_id: int
    teacher_id: int
    discipline_id: int
    discipline_name: str
    starts_at: datetime
    ends_at: datetime
    description: str | None
    address: str | None = None
    city_id: int | None = None
    city_name: str | None = None
    capacity: int
    reserved_seats: int
    available_seats: int
    is_active: bool
    completed_at: datetime | None = None
    created_at: datetime

    @computed_field
    @property
    def display_status(self) -> LessonDisplayStatus:
        return resolve_slot_display_status(self.is_active, self.starts_at, self.ends_at, self.completed_at)


class AvailableSlotReadDTO(BaseModel):
    slot_id: int
    teacher_id: int
    teacher_name: str
    city_id: int
    city_name: str
    discipline_id: int
    discipline_name: str
    starts_at: datetime
    ends_at: datetime
    description: str | None
    address: str | None = None
    capacity: int
    reserved_seats: int
    available_seats: int
    average_rating: float | None = None
    reviews_count: int = 0

    @computed_field
    @property
    def display_status(self) -> LessonDisplayStatus:
        return resolve_time_based_display_status(self.starts_at, self.ends_at)


class BookingCreateDTO(BaseModel):
    student_id: int = Field(gt=0)
    slot_id: int = Field(gt=0)


class BookingReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    slot_id: int
    status: BookingStatus
    created_at: datetime

    @computed_field
    @property
    def display_status(self) -> LessonDisplayStatus:
        if self.status == BookingStatus.CANCELLED:
            return LessonDisplayStatus.CANCELLED
        if self.status == BookingStatus.COMPLETED:
            return LessonDisplayStatus.COMPLETED
        return LessonDisplayStatus.UPCOMING


class BookingDetailsReadDTO(BaseModel):
    booking_id: int
    student_id: int
    student_name: str
    student_email: str
    slot_id: int
    teacher_id: int
    teacher_name: str
    city_id: int
    city_name: str
    discipline_id: int
    discipline_name: str
    starts_at: datetime
    ends_at: datetime
    description: str | None
    address: str | None = None
    status: BookingStatus
    has_review: bool = False
    created_at: datetime

    @computed_field
    @property
    def display_status(self) -> LessonDisplayStatus:
        return resolve_booking_display_status(self.status, self.starts_at, self.ends_at)


class TeacherSlotBookingReadDTO(BaseModel):
    booking_id: int
    student_id: int
    student_name: str
    student_email: str
    status: BookingStatus
    display_status: LessonDisplayStatus | None = None
    created_at: datetime


class TeacherSlotBulkBookingActionReadDTO(BaseModel):
    slot_id: int
    updated_bookings: int


class ReviewCreateDTO(BaseModel):
    booking_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ReviewReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    teacher_id: int
    student_id: int
    rating: int
    comment: str | None
    created_at: datetime


class ReviewListReadDTO(BaseModel):
    review_id: int
    booking_id: int
    teacher_id: int
    teacher_name: str
    student_id: int
    student_name: str
    discipline_id: int
    discipline_name: str
    rating: int
    comment: str | None
    created_at: datetime


class NotificationReadDTO(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


class AnalyticsOverviewReadDTO(BaseModel):
    total_cities: int
    total_disciplines: int
    total_teachers: int
    total_students: int
    filtered_slots_total: int
    filtered_slots_active: int
    filtered_bookings_total: int
    filtered_capacity_total: int
    filtered_reserved_seats_total: int
    utilization_rate_percent: float = Field(ge=0, le=100)


class TeacherAnalyticsReadDTO(BaseModel):
    teacher_id: int
    teacher_name: str
    city_id: int
    city_name: str
    slots_total: int
    slots_active: int
    bookings_total: int
    capacity_total: int
    reserved_seats_total: int
    utilization_rate_percent: float = Field(ge=0, le=100)
    average_rating: float | None = None


class DisciplineAnalyticsReadDTO(BaseModel):
    discipline_id: int
    discipline_name: str
    slots_total: int
    slots_active: int
    bookings_total: int
    capacity_total: int
    reserved_seats_total: int
    utilization_rate_percent: float = Field(ge=0, le=100)
