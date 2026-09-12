from fastapi import APIRouter, Depends, HTTPException, Response, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.auth import verify_password, create_access_token

router = APIRouter()

@router.post("/login")
def login(
    response: Response, 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    token = create_access_token(data={"sub": user.email})
    # Set token in a secure cookie so the browser remembers it
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return {"message": "success"}

@router.get("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "logged out"}