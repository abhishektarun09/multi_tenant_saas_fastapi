from fastapi import status, HTTPException, Depends, APIRouter, Request, Response
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.users import Users
from core.utils import verify, audit_logs
from api.v2.schemas.authorization_schemas import LoginOut
from database.db.session import get_db
from core.oauth2 import create_access_token, create_refresh_token
from core.config import env

REFRESH_TOKEN_EXPIRE_DAYS = env.refresh_token_expire_days

router = APIRouter()


@router.post("/login", response_model=LoginOut)
async def login(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_credentials: OAuth2PasswordRequestForm = Depends(),
):

    stmt = select(Users).where(
        Users.email == user_credentials.username,
        Users.is_deleted == False,
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not verify(user_credentials.password, user.password_hash):
        await audit_logs(
            db=db,
            action="login.failed",
            resource_type="auth",
            status="failed",
            meta_data={
                "reason": "invalid_credentials",
                "email": user_credentials.username,
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint="/login",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials"
        )

    await audit_logs(
        db=db,
        actor_user_id=user.id,
        action="login.success",
        resource_type="auth",
        resource_id=str(user.id),
        meta_data={"email": user.email},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        endpoint="/login",
    )

    access_token_data = {
        "user_id": user.id,
        "token_type": "access",
    }

    refresh_token_data = {
        "user_id": user.id,
        "token_type": "refresh",
    }

    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=(REFRESH_TOKEN_EXPIRE_DAYS * 60 * 60 * 24),
    )

    return {"access_token": access_token, "token_type": "bearer"}
