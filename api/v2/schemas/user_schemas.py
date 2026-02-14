from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from pydantic import ConfigDict


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRegisterResponse(BaseModel):
    message: str
    user: UserOut


class Me(BaseModel):
    email: EmailStr
    name: str
    role: str


class UpdatePasswordOut(BaseModel):
    response: str
    action_required: str


class UpdatePasswordIn(BaseModel):
    current_password: str
    new_password: str
