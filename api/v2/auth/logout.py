from fastapi import Depends, APIRouter, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from core.rate_limiter import RateLimiter
from database.models.jti_blocklist import JtiBlocklist
from core.utils import get_valid_refresh_payload
from api.v2.schemas.authorization_schemas import LogoutResponse
from database.db.session import get_db

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.post("/logout", response_model=LogoutResponse)
async def logout(
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

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return {"response": "Logged out successfully"}
