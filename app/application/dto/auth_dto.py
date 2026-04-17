from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.application.dto.email_validation import (
    ensure_not_common_email_typo,
    normalize_email_input,
)
from app.domain.entities.user_account import UserRole


class StudentRegisterDTO(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=255)
    city_id: int = Field(gt=0)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()

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
    full_name: str | None = None
    email: str | None = None
    city_id: int | None = None
    city_name: str | None = None
    created_at: datetime


class AccountUpdateDTO(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=120)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    current_password: str | None = Field(default=None, min_length=6, max_length=128)
    new_password: str | None = Field(default=None, min_length=6, max_length=128)
    city_id: int | None = Field(default=None, gt=0)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("username cannot be blank")
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("full_name cannot be blank")
        return normalized

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return normalize_email_input(value)

    @field_validator("email")
    @classmethod
    def validate_email_domain_typo(cls, value: EmailStr | None) -> EmailStr | None:
        return ensure_not_common_email_typo(value)

    @field_validator("current_password", "new_password")
    @classmethod
    def strip_passwords(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def validate_payload(self) -> "AccountUpdateDTO":
        if (
            self.username is None
            and self.full_name is None
            and self.email is None
            and self.current_password is None
            and self.new_password is None
            and self.city_id is None
        ):
            raise ValueError("At least one field must be provided for account update.")

        has_current_password = self.current_password is not None
        has_new_password = self.new_password is not None
        if has_current_password != has_new_password:
            raise ValueError("current_password and new_password must be provided together.")

        return self


class TeacherAccountCreateDTO(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    teacher_id: int = Field(gt=0)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("full_name cannot be blank")
        return normalized

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return normalize_email_input(value)

    @field_validator("email")
    @classmethod
    def validate_email_domain_typo(cls, value: EmailStr | None) -> EmailStr | None:
        return ensure_not_common_email_typo(value)


class AdminBootstrapDTO(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()
