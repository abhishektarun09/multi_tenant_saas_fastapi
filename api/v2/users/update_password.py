from fastapi import Request, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.oauth2 import get_current_user
from core.rate_limiter import RateLimiter
from database.models.auth_identities import AuthIdentity
from database.models.jti_blocklist import JtiBlocklist
from database.models.users import Users
from core.utils import audit_logs, get_valid_refresh_payload, hash, verify
from api.v2.schemas.user_schemas import (
    UpdatePasswordIn,
    UpdatePasswordOut,
)
from database.db.session import get_db


router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.patch(
    "/update-password", response_model=UpdatePasswordOut, status_code=status.HTTP_200_OK
)
async def update_password(
    response: Response,
    request: Request,
    input_data: UpdatePasswordIn,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    identity = (
        (
            await db.execute(
                select(AuthIdentity)
                .join(Users, Users.id == AuthIdentity.user_id)
                .where(
                    current_user.id == Users.id,
                    Users.is_deleted.is_(False),
                    AuthIdentity.provider == "password",
                )
            )
        )
        .scalars()
        .first()
    )

    if not verify(input_data.current_password, identity.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if verify(input_data.new_password, identity.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    payload = await get_valid_refresh_payload(request, db)

    jti_value = payload.jti
    blacklisted_jti = JtiBlocklist(jti=jti_value)

    db.add(blacklisted_jti)
    hashed_password = hash(input_data.new_password)
    identity.password_hash = hashed_password

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
        samesite="lax",
    )

    return {
        "response": "Password updated. Please log in again",
        "action_required": "reauthenticate",
    }
