from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.domain.entities.user_account import UserRole


class StudentRegisterDTO(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    city_id: int = Field(gt=0)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return value.strip()


class LoginDTO(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class TokenReadDTO(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: UserRole
    student_id: int | None
    teacher_id: int | None


class AccountReadDTO(BaseModel):
    user_id: int
    username: str
    role: UserRole
    student_id: int | None
    teacher_id: int | None
    created_at: datetime


class TeacherAccountCreateDTO(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    teacher_id: int = Field(gt=0)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class AdminBootstrapDTO(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()
