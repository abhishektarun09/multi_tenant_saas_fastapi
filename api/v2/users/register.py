import uuid
from fastapi import Request, status, HTTPException, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from core.rate_limiter import RateLimiter
from database.models.auth_identities import AuthIdentity
from database.models.users import Users
from core.utils import audit_logs, hash
from api.v2.schemas.user_schemas import (
    UserCreate,
    UserRegisterResponse,
)
from database.db.session import get_db
from sqlalchemy import select

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRegisterResponse,
)
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
    new_user = Users(**user_data)

    db.add(new_user)
    await db.flush()

    identity = AuthIdentity(
        id=uuid.uuid4(),
        user_id=new_user.id,
        provider="password",
        password_hash=hashed_password,
    )
    db.add(identity)

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

    return {
        "message": "Account created!",
        "user": new_user,
    }
