from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.organization import Organization
from database.models.organization_member import OrganizationMember
from api.v1.schemas.authorization_schemas import Token
from api.v1.schemas.organization_schemas import (
    ListUsers,
    OrganizationCreate,
    OrganizationOut,
    SelectOrganization,
    AddUsers,
    AddUsersOut,
    UpdateOrgIn,
    UpdateOrgOut,
)
from database.models.users import Users
from database.db.session import get_db
from core.utils import slugify, audit_logs
from core.oauth2 import create_access_token, get_current_user, get_user_and_membership

router = APIRouter(prefix="/organization", tags=["Organizations"])


# JWT Protected
@router.post("/select", status_code=status.HTTP_202_ACCEPTED, response_model=Token)
async def select_organization(
    organization: SelectOrganization,
    db: AsyncSession = Depends(get_db),
    current_user: int = Depends(get_current_user),
):

    user_id = current_user.id
    org_id = organization.org_id
    member = (
        (
            await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == user_id,
                )
            )
        )
        .scalars()
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not member of the organization",
        )

    jwt_data = {"user_id": user_id, "org_id": org_id, "token_type": "access"}

    jwt_token = create_access_token(jwt_data)

    return {"access_token": jwt_token, "token_type": "bearer"}


# JWT Protected
@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=OrganizationOut
)
async def register_organization(
    request: Request,
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: int = Depends(get_current_user),
):

    slug_name = slugify(organization.name)

    # Check if organization with the same name already exists
    existing_organization = (
        (
            await db.execute(
                select(Organization).where(
                    Organization.slug == slug_name,
                    Organization.is_deleted == False,
                )
            )
        )
        .scalars()
        .first()
    )

    if existing_organization:
        await audit_logs(
            db=db,
            actor_user_id=current_user.id,
            action="creation.failed",
            resource_type="organizations",
            status="failed",
            meta_data={"org_slug": slug_name},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/register",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already registered",
        )

    new_organization = organization.model_dump()
    new_organization["slug"] = slug_name
    new_organization = Organization(**new_organization)

    db.add(new_organization)
    await db.flush()

    membership = OrganizationMember(
        user_id=current_user.id, organization_id=new_organization.id, role="owner"
    )
    db.add(membership)

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        action="org.registered",
        resource_type="organizations",
        resource_id=str(new_organization.id),
        status="success",
        meta_data={"org_slug": slug_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/organization/register",
    )

    return new_organization


@router.put("/update", status_code=status.HTTP_201_CREATED, response_model=UpdateOrgOut)
async def update(
    request: Request,
    payload: UpdateOrgIn,
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    user, membership = current_user_and_membership

    if membership.role.value not in ("owner", "admin"):
        await audit_logs(
            db=db,
            actor_user_id=user.id,
            action="update.failed",
            resource_type="organizations",
            organization_id=membership.organization_id,
            resource_id=str(membership.organization_id),
            status="failed",
            meta_data={"new_name": payload.new_name, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/update",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to add users to organization",
        )

    new_slug_name = slugify(payload.new_name)

    existing_organization = (
        (
            await db.execute(
                select(Organization).where(
                    Organization.slug == new_slug_name,
                    Organization.is_deleted == False,
                )
            )
        )
        .scalars()
        .first()
    )

    if existing_organization:
        await audit_logs(
            db=db,
            actor_user_id=user.id,
            action="update.failed",
            resource_type="organizations",
            organization_id=membership.organization_id,
            resource_id=str(membership.organization_id),
            status="failed",
            meta_data={"new_name": payload.new_name, "role": membership.role.value},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            endpoint="/organization/update",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already registered",
        )

    updated_org = Organization(name=payload.new_name, slug=new_slug_name)

    db.add(updated_org)
    await audit_logs(
        db=db,
        actor_user_id=user.id,
        action="org.updated",
        resource_type="organizations",
        organization_id=membership.organization_id,
        resource_id=str(membership.organization_id),
        status="success",
        meta_data={"new_name": payload.new_name, "role": membership.role.value},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/organization/update",
    )

    return {"message": "Organization details updated"}


# JWT Protected
@router.post(
    "/add_user", status_code=status.HTTP_201_CREATED, response_model=AddUsersOut
)
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
                    Users.email == input.email,
                    Users.is_deleted == False,
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
                    Users.is_deleted == False,
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


@router.get("/list_users", status_code=status.HTTP_200_OK, response_model=ListUsers)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    user, membership = current_user_and_membership

    if membership.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view users organization",
        )

    users_in_org = (
        (
            await db.execute(
                select(Users)
                .join(OrganizationMember, OrganizationMember.user_id == Users.id)
                .where(
                    OrganizationMember.organization_id == membership.organization_id,
                    Users.is_deleted == False,
                )
            )
        )
        .scalars()
        .all()
    )

    if not users_in_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No users in Organization"
        )

    user_details = [{"name": user.name, "email": user.email} for user in users_in_org]

    return {"user_details": user_details}
