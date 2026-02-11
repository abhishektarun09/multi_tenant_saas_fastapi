from typing import List
from pydantic import BaseModel, EmailStr


class AddProjectsOut(BaseModel):
    name: str
    organization_id: int
    created_by: int


class AddProjectsIn(BaseModel):
    name: str


class AddUsersOut(BaseModel):
    user_id: int
    project_id: int


class AddUsersIn(BaseModel):
    email: EmailStr
    project_id: int


class UpdateProjectsIn(BaseModel):
    new_name: str


class UpdateProjectsOut(BaseModel):
    response: str


class Project(BaseModel):
    id: int
    name: str


class ListProjects(BaseModel):
    project_details: List[Project]


class ProjectMembersOut(BaseModel):
    name: str
    email: str


class ListMembers(BaseModel):
    member_details: List[ProjectMembersOut]


class RemoveUsersOut(BaseModel):
    response: str


class RemoveUsersIn(BaseModel):
    email: EmailStr
    project_id: int
