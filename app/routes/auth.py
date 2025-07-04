from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth import authenticate_user, create_access_token, verify_token
from app.services.user_service import UserService
from app.models.user import User, UserRole
from app.models.activity import ActivityType
from app.config import settings
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def get_current_user_cookie(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user using cookie authentication"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=403, detail="Not authenticated")

    # Remove 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=403, detail="Invalid token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=403, detail="Invalid token")

    user = UserService.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=403, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    return user


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Authenticate user and create session"""
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "Incorrect username or password"
            },
            status_code=400
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Log login activity with IP and user agent
    from app.utils.request_utils import log_user_activity
    log_user_activity(
        db=db,
        user_id=user.id,
        activity_type="login",
        description="تسجيل دخول المستخدم",
        request=request
    )
    
    # Create response with redirect
    if user.role == UserRole.ADMIN:
        response = RedirectResponse(url="/admin/dashboard", status_code=302)
    else:
        response = RedirectResponse(url="/dashboard", status_code=302)
    
    # Set token in cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        secure=False  # Set to True in production with HTTPS
    )
    
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Display registration page"""
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Register new user"""
    # Validate password confirmation
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "Passwords do not match"
            },
            status_code=400
        )
    
    try:
        # Create user
        user = UserService.create_user(
            db=db,
            username=username,
            email=email,
            full_name=full_name,
            password=password
        )
        
        # Log registration activity
        from app.utils.request_utils import log_user_activity
        log_user_activity(
            db=db,
            user_id=user.id,
            activity_type="profile_updated",
            description="تسجيل مستخدم جديد",
            request=request
        )
        
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "success": "Registration successful! Please log in."
            }
        )
        
    except HTTPException as e:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": e.detail
            },
            status_code=400
        )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Logout user"""
    # Log logout activity
    from app.utils.request_utils import log_user_activity
    log_user_activity(
        db=db,
        user_id=current_user.id,
        activity_type="logout",
        description="تسجيل خروج المستخدم",
        request=request
    )
    
    # Create response with redirect
    response = RedirectResponse(url="/login", status_code=302)
    
    # Clear token cookie
    response.delete_cookie(key="access_token")
    
    return response


# API endpoints for token-based authentication
@router.post("/api/token", response_model=Token)
async def login_for_access_token(
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """API endpoint for token-based authentication"""
    user = authenticate_user(db, user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
