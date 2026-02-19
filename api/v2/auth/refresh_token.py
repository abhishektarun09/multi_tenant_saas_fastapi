from fastapi import Depends, APIRouter, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from core.rate_limiter import RateLimiter
from database.models.jti_blocklist import JtiBlocklist
from core.utils import get_valid_refresh_payload
from api.v2.schemas.authorization_schemas import Token
from database.db.session import get_db
from core.oauth2 import create_access_token, create_refresh_token
from core.config import env

REFRESH_TOKEN_EXPIRE_DAYS = env.refresh_token_expire_days

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    response: Response, request: Request, db: AsyncSession = Depends(get_db)
):

    payload = await get_valid_refresh_payload(request, db)

    jti_value = payload.jti
    blacklisted_jti = JtiBlocklist(jti=jti_value)

    try:
        db.add(blacklisted_jti)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    access_token_data = {
        "user_id": payload.user_id,
        "token_type": "access",
    }

    refresh_token_data = {
        "user_id": payload.user_id,
        "token_type": "refresh",
    }

    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=(REFRESH_TOKEN_EXPIRE_DAYS * 60 * 60 * 24),
    )

    return {"access_token": access_token, "token_type": "bearer"}
