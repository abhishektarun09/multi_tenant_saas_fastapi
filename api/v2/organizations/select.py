from fastapi import status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.organization_member import OrganizationMember
from api.v2.schemas.authorization_schemas import Token
from database.db.session import get_db
from core.oauth2 import create_access_token, get_current_user

router = APIRouter()


@router.post(
    "/select/{organization_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Token,
)
async def select_organization(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: int = Depends(get_current_user),
):

    user_id = current_user.id
    org_id = organization_id
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

    jwt_data = {
        "user_id": user_id,
        "org_id": org_id,
        "token_type": "access",
    }

    jwt_token = create_access_token(jwt_data)

    return {"access_token": jwt_token, "token_type": "bearer"}
