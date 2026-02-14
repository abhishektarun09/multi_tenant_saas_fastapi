from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.rate_limiter import RateLimiter
from core.utils import decode_url_safe_token
from database.db.session import get_db
from database.models.users import Users

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.get("/verify/{token}")
async def verify_account(token: str, db: AsyncSession = Depends(get_db)):

    token_data = decode_url_safe_token(token)

    if "email" not in token_data:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = (
        (await db.execute(select(Users).where(Users.email == token_data["email"])))
        .scalars()
        .first()
    )

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification link")

    if user.is_verified:
        return {"response": "Account already verified"}

    user.is_verified = True

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    return {"response": "Account verified successfully"}
