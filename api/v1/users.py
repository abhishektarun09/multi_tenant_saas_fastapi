from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from database.models.users import Users
from core.utils import hash, verify
from database.schemas.user_schemas import UserCreate, UserOut
from database.db.base import get_db

router = APIRouter(
    prefix="/users",
    tags=['Users']
)

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    
    # Check if user with the same email already exists
    existing_user = db.query(Users).filter(Users.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # hash the password - user.password
    hashed_password = hash(user.password_hash)
    
    user_data = user.model_dump()
    user_data['password_hash'] = hashed_password
    new_user = Users(**user_data)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.get('/{id}', response_model=UserOut)
async def get_user(id: int, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with id: {id} does not exist")

    return user