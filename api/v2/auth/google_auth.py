import uuid
from fastapi import (
    Request,
    status,
    HTTPException,
    Depends,
    APIRouter,
)
from authlib.integrations.starlette_client import OAuthError
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from api.v2.schemas.authorization_schemas import GoogleUser
from core.oauth2 import create_access_token, create_refresh_token
from core.rate_limiter import RateLimiter
from database.models.auth_identities import AuthIdentity
from database.models.users import Users
from core.utils import audit_logs
from database.db.session import get_db
from sqlalchemy import select
from core.config import env
from core.oauth2 import oauth
from authlib.oauth2.rfc6749 import OAuth2Token

REFRESH_TOKEN_EXPIRE_DAYS = env.refresh_token_expire_days

router = APIRouter(dependencies=[Depends(RateLimiter(max_calls=10, time_frame=60))])

GOOGLE_REDIRECT_URI = f"{env.base_url}/v2/auth/callback/google"


@router.get("/google")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@router.get("/callback/google")
async def auth_google(
    request: Request,
    db: AsyncSession = Depends(get_db),
):

    try:
        google_token: OAuth2Token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    resp = await oauth.google.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        token=google_token,
    )

    user_info = resp.json()

    google_user = GoogleUser(**user_info)

    if not google_user.verified_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account not verified"
        )

    existing_user = (
        (
            await db.execute(
                select(Users).where(
                    Users.email == google_user.email, Users.is_deleted.is_(False)
                )
            )
        )
        .scalars()
        .first()
    )

    if not existing_user:
        new_user = Users(name=google_user.name, email=google_user.email)

        db.add(new_user)
        await db.flush()

        existing_user = new_user

        new_user_identity = AuthIdentity(
            id=uuid.uuid4(),
            user_id=new_user.id,
            provider="google",
            provider_user_id=google_user.id,
        )
        db.add(new_user_identity)

        await audit_logs(
            db=db,
            actor_user_id=new_user.id,
            action="user.registered",
            resource_type="auth",
            resource_id=str(new_user.id),
            meta_data={"name": google_user.name, "email": google_user.email},
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint="/google_auth",
        )

    existing_google_user = (
        (
            await db.execute(
                select(AuthIdentity).where(
                    AuthIdentity.provider == "google",
                    AuthIdentity.provider_user_id == google_user.id,
                )
            )
        )
        .scalars()
        .first()
    )

    if not existing_google_user:
        new_user_identity = AuthIdentity(
            id=uuid.uuid4(),
            user_id=existing_user.id,
            provider="google",
            provider_user_id=google_user.id,
        )
        db.add(new_user_identity)

        await audit_logs(
            db=db,
            actor_user_id=existing_user.id,
            action="user.registered",
            resource_type="auth",
            resource_id=str(existing_user.id),
            meta_data={"name": google_user.name, "email": google_user.email},
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint="/google_auth",
        )

    access_token_data = {
        "user_id": existing_user.id,
        "token_type": "access",
    }

    refresh_token_data = {
        "user_id": existing_user.id,
        "token_type": "refresh",
    }

    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)

    html = f"""
    <html>
        <body>
            <h2>Login Successful</h2>
            <p>Copy your access token and paste it into Swagger Authorize:</p>
            <textarea rows="8" cols="100">{access_token}</textarea>
            <br><br>
            <a href="{env.base_url}/docs">Go back to Swagger</a>
        </body>
    </html>
    """

    response = HTMLResponse(content=html)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=(REFRESH_TOKEN_EXPIRE_DAYS * 60 * 60 * 24),
    )

    return response
