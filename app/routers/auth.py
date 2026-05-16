import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel as PydanticBase
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Employee, User
from ..models.schemas import Token, UserCreate, UserLogin
from ..utils.auth import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "employee_id": user.employee_id,
        },
    }


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    employee_id = None
    if user_data.role == "employee":
        # Link to existing Employee record if HR already imported this email
        existing_emp = db.query(Employee).filter(Employee.email == user_data.email).first()
        if existing_emp:
            employee_id = existing_emp.id
        else:
            name = user_data.name or user_data.email.split("@")[0]
            emp = Employee(name=name, email=user_data.email)
            db.add(emp)
            db.flush()
            employee_id = emp.id

    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        employee_id=employee_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return _token_response(user)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "employee_id": current_user.employee_id,
    }


class GoogleAuthRequest(PydanticBase):
    credential: str  # The Google ID token

@router.post("/google", response_model=Token)
async def google_login(body: GoogleAuthRequest, db: Session = Depends(get_db)):
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": body.credential}
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    data = resp.json()
    if data.get("aud") != google_client_id:
        raise HTTPException(status_code=400, detail="Token audience mismatch")

    email = data["email"]
    name  = data.get("name", email.split("@")[0])

    user = db.query(User).filter(User.email == email).first()
    if not user:
        emp = Employee(name=name, email=email)
        db.add(emp)
        db.flush()
        user = User(
            email=email,
            hashed_password=hash_password(os.urandom(32).hex()),
            role="employee",
            employee_id=emp.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return _token_response(user)
