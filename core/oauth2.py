import orjson
import uuid
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import env
from database.models.users import Users
from database.models.organization_member import OrganizationMember
from api.v2.schemas.authorization_schemas import TokenData
from database.db.session import get_db
from typing import Tuple
from sqlalchemy import select
from authlib.integrations.starlette_client import OAuth
from core.redis.redis_config import redis_client as redis
from core.redis.schemas import UserSchema, OrganizationMemberSchema


bearer_scheme = HTTPBearer()

SECRET_KEY = env.secret_key
ALGORITHM = env.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = env.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = env.refresh_token_expire_days

GOOGLE_CLIENT_ID = env.google_client_id
GOOGLE_CLIENT_SECRET = env.google_client_secret

oauth = OAuth()

oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
    },
)


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    to_encode["jti"] = str(uuid.uuid4())

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    to_encode["jti"] = str(uuid.uuid4())

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str, credentials_exception):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        org_id = payload.get("org_id")
        token_type = payload.get("token_type")
        jti = payload.get("jti")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(
            user_id=user_id, org_id=org_id, token_type=token_type, jti=jti
        )
    except JWTError:
        raise credentials_exception

    return token_data


def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
    return verify_token(token, credentials_exception)


async def get_current_user(
    payload=Depends(get_token_payload), db: AsyncSession = Depends(get_db)
):
    cache_key = f"user_id:{payload.user_id}"
    cached_user = await redis.get(cache_key)

    if cached_user:
        cached_data = orjson.loads(cached_user)
        return UserSchema.model_validate(cached_data)

    else:
        user = (
            (
                await db.execute(
                    select(Users).where(
                        Users.id == payload.user_id,
                        Users.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        user_data = UserSchema.model_validate(user)

        await redis.set(cache_key, orjson.dumps(user_data.model_dump()), ex=60 * 5)

        return user_data


async def get_membership(
    payload=Depends(get_token_payload), db: AsyncSession = Depends(get_db)
):

    version_key = f"org_id:{payload.org_id}:version"
    version = await redis.get(version_key)
    if not version:
        version = 1
        await redis.set(version_key, version)

    cache_key = f"org_id:{payload.org_id}:v{version}:user_id:{payload.user_id}"
    cached_member = await redis.get(cache_key)

    if cached_member:
        cached_data = orjson.loads(cached_member)
        return OrganizationMemberSchema.model_validate(cached_data)

    else:
        org_id = payload.org_id

        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization not selected",
            )

        # admin, member etc.
        membership = (
            (
                await db.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.user_id == payload.user_id,
                        OrganizationMember.organization_id == org_id,
                    )
                )
            )
            .scalars()
            .first()
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this Organization or Organization does not exist anymore/deleted.",
            )

        membership_data = OrganizationMemberSchema.model_validate(membership)

        await redis.set(
            cache_key, orjson.dumps(membership_data.model_dump()), ex=60 * 5
        )

        return membership_data


def get_user_and_membership(
    user=Depends(get_current_user), membership=Depends(get_membership)
) -> Tuple[Users, OrganizationMember]:
    return user, membership
