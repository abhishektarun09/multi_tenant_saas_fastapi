from fastapi import Request, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from core.oauth2 import get_current_user, get_user_and_membership
from database.models.jti_blocklist import JtiBlocklist
from database.models.organization_member import OrganizationMember
from database.models.users import Users
from core.utils import audit_logs, get_valid_refresh_payload, hash, verify
from api.v1.schemas.organization_schemas import ListOrgs
from api.v1.schemas.user_schemas import (
    UpdatePasswordIn,
    UpdatePasswordOut,
    UserCreate,
    UserOut,
    Me,
)
from database.db.session import get_db
from sqlalchemy import select

router = APIRouter(prefix="/user", tags=["Users"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def register_user(
    request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)
):

    # Check if user with the same email already exists

    existing_user = (
        (
            await db.execute(
                select(Users).where(
                    Users.email == user.email, Users.is_deleted.is_(False)
                )
            )
        )
        .scalars()
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # hash the password - user.password
    hashed_password = hash(user.password)

    user_data = user.model_dump(exclude={"password"})
    user_data["password_hash"] = hashed_password

    new_user = Users(**user_data)

    db.add(new_user)
    await db.flush()

    await audit_logs(
        db=db,
        actor_user_id=new_user.id,
        action="user.registered",
        resource_type="users",
        resource_id=str(new_user.id),
        meta_data={"name": user.name, "email": user.email},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        endpoint="/register",
    )

    return new_user


@router.get("/me", response_model=Me)
async def me(
    db: AsyncSession = Depends(get_db),
    current_user_and_membership=Depends(get_user_and_membership),
):

    current_user, membership = current_user_and_membership

    user_details = (
        (
            await db.execute(
                select(Users).where(
                    Users.id == current_user.id, Users.is_deleted.is_(False)
                )
            )
        )
        .scalars()
        .first()
    )

    return {
        "email": user_details.email,
        "name": user_details.name,
        "role": membership.role,
    }


@router.get("/orgs", response_model=ListOrgs)
async def list_orgs(
    db: AsyncSession = Depends(get_db), current_user: int = Depends(get_current_user)
):

    user = (
        (
            await db.execute(
                select(Users).where(
                    Users.id == current_user.id, Users.is_deleted.is_(False)
                )
            )
        )
        .scalars()
        .first()
    )

    # List out the organizations the user is part of for frontend to select
    org_ids = (
        (
            await db.execute(
                select(OrganizationMember.organization_id).where(
                    OrganizationMember.user_id == user.id
                )
            )
        )
        .scalars()
        .all()
    )

    return {"email": user.email, "org_ids": org_ids}


@router.patch(
    "/update_password", response_model=UpdatePasswordOut, status_code=status.HTTP_200_OK
)
async def update_password(
    response: Response,
    request: Request,
    input_data: UpdatePasswordIn,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    if not verify(input_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if verify(input_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    payload = await get_valid_refresh_payload(request, db)

    jti_value = payload.jti
    blacklisted_jti = JtiBlocklist(jti=jti_value)

    db.add(blacklisted_jti)
    hashed_password = hash(input_data.new_password)
    current_user.password_hash = hashed_password

    await audit_logs(
        db=db,
        actor_user_id=current_user.id,
        action="password.changed",
        resource_type="users",
        resource_id=str(current_user.id),
        meta_data={"email": current_user.email},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        endpoint="/update_password",
    )

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return {
        "response": "Password updated. Please log in again",
        "action_required": "reauthenticate",
    }
