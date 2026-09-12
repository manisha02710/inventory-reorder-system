from fastapi import APIRouter, Depends, HTTPException, Response, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.auth import verify_password, create_access_token, get_password_hash

router = APIRouter()


@router.post("/guest")
def guest_login(response: Response):
    """Instant 1-click guest login for evaluators and visitors without passwords."""
    token = create_access_token(data={"sub": "Guest Viewer"})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return {"message": "success", "user": "Guest Viewer"}


@router.post("/register")
def register(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    email_clean = email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Please enter a valid email address")

    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists. Please sign in.")

    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long")

    new_user = User(
        email=email_clean,
        hashed_password=get_password_hash(password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={"sub": new_user.email})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return {"message": "registered", "email": new_user.email}


@router.post("/login")
def login(
    response: Response, 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    email_clean = email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    token = create_access_token(data={"sub": user.email})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return {"message": "success"}


@router.get("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "logged out"}