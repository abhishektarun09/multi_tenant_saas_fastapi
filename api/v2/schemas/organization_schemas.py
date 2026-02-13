from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Literal, List
from datetime import datetime


class OrganizationCreate(BaseModel):
    name: str


class OrganizationOut(BaseModel):
    id: int
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddUsers(BaseModel):
    email: EmailStr
    role: Literal["member", "owner", "admin"]


class AddUsersOut(BaseModel):
    message: str


class ListOrgs(BaseModel):
    email: EmailStr
    org_ids: List[int]


class UserOut(BaseModel):
    name: str
    email: str


class ListUsers(BaseModel):
    user_details: List[UserOut]


class UpdateOrgIn(BaseModel):
    new_name: str = Field(..., min_length=1)


class UpdateOrgOut(BaseModel):
    message: str


class DeleteOrganizationOut(BaseModel):
    response: str
    action: str


class RemoveMemberOut(BaseModel):
    response: str


class RemoveMemberIn(BaseModel):
    email: EmailStr
