from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    discipline_ids: list[int] = Field(min_length=1)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        return value.strip()


class TeacherReadDTO(BaseModel):
    id: int
    full_name: str
    city_id: int
    discipline_ids: list[int]


class StudentCreateDTO(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    city_id: int = Field(gt=0)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


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
    capacity: int = Field(default=1, gt=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_time_range(self) -> "TeacherSlotCreateDTO":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class TeacherSlotManageCreateDTO(BaseModel):
    discipline_id: int = Field(gt=0)
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(default=1, gt=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_time_range(self) -> "TeacherSlotManageCreateDTO":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class TeacherSlotUpdateDTO(BaseModel):
    discipline_id: int | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update_payload(self) -> "TeacherSlotUpdateDTO":
        has_any_field = any(
            value is not None
            for value in (
                self.discipline_id,
                self.starts_at,
                self.ends_at,
                self.capacity,
                self.is_active,
            )
        )
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
    capacity: int
    is_active: bool
    created_at: datetime


class TeacherSlotDetailsReadDTO(BaseModel):
    slot_id: int
    teacher_id: int
    discipline_id: int
    discipline_name: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    reserved_seats: int
    available_seats: int
    is_active: bool
    created_at: datetime


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
    capacity: int
    reserved_seats: int
    available_seats: int


class BookingCreateDTO(BaseModel):
    student_id: int = Field(gt=0)
    slot_id: int = Field(gt=0)


class BookingReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    slot_id: int
    created_at: datetime


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


class DisciplineAnalyticsReadDTO(BaseModel):
    discipline_id: int
    discipline_name: str
    slots_total: int
    slots_active: int
    bookings_total: int
    capacity_total: int
    reserved_seats_total: int
    utilization_rate_percent: float = Field(ge=0, le=100)
