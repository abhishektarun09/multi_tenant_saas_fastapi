import re

from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime
from pydantic import ConfigDict


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if v != v.strip():
            raise ValueError("Password must not contain leading or trailing spaces")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")

        return v


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRegisterResponse(BaseModel):
    message: str
    user: UserOut


class Me(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    org_id: int
    role: str


class UpdatePasswordOut(BaseModel):
    response: str
    action_required: str


class UpdatePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if v != v.strip():
            raise ValueError("Password must not contain leading or trailing spaces")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")

        return v
