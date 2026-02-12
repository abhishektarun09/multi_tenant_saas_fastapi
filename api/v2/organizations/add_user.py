from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.organization_member import OrganizationMember
from api.v2.schemas.organization_schemas import (
    AddUsers,
    AddUsersOut,
)
from database.models.users import Users
from database.db.session import get_db
from core.utils import audit_logs
from core.oauth2 import get_user_and_membership

router = APIRouter()


@router.post("/member", status_code=status.HTTP_201_CREATED, response_model=AddUsersOut)
async def add_user(
    request: Request,
    input: AddUsers,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    if membership.role.value not in ("owner", "admin"):
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="addition.failed",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"email": input.email, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/add_user",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to add users to organization",
        )

    if membership.role.value == "admin" and input.role == "owner":
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="addition.failed",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={
                "reason": "admin trying to add owner",
                "email": input.email,
                "role": membership.role.value,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/add_user",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to add owner",
        )

    existing_user = (
        (
            await db.execute(
                select(Users).where(
                    Users.email == input.email, Users.is_deleted.is_(False)
                )
            )
        )
        .scalars()
        .first()
    )

    if not existing_user:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="addition.failed",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"email": input.email, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/add_user",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist"
        )

    member = (
        (
            await db.execute(
                select(Users)
                .join(OrganizationMember, OrganizationMember.user_id == Users.id)
                .where(
                    Users.email == input.email,
                    OrganizationMember.organization_id == membership.organization_id,
                    Users.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .first()
    )

    if member:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="addition.failed",
            resource_type="organizations",
            organization_id=membership.organization_id,
            status="failed",
            meta_data={"email": input.email, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/add_user",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered in Organization",
        )

    new_member = OrganizationMember(
        user_id=existing_user.id,
        organization_id=membership.organization_id,
        role=input.role,
    )

    db.add(new_member)
    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        action="user.added",
        resource_type="organizations",
        organization_id=membership.organization_id,
        status="success",
        meta_data={"email": input.email, "role": membership.role.value},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/organization/add_user",
    )

    return {"message": "User added to organization"}
