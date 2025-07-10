from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth import authenticate_user, create_access_token, verify_token, verify_password
from app.services.user_service import UserService
from app.models.user import User, UserRole, UserStatus
from app.models.activity import ActivityType
from app.config import settings
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

logger = logging.getLogger(__name__)

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
    # Preserve username for potential re-display (but not password for security)
    form_data = {"username": username}

    # First check if user exists and password is correct
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "اسم المستخدم أو كلمة المرور غير صحيحة",
                "form_data": form_data
            },
            status_code=400
        )

    # Check approval status for specific error messages (skip for admin users)
    if user.role != UserRole.ADMIN:
        if user.approval_status == UserStatus.PENDING:
            return templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "error": "حسابك في انتظار موافقة الإدارة. يرجى انتظار الموافقة قبل تسجيل الدخول.",
                    "form_data": form_data
                },
                status_code=403
            )
        elif user.approval_status == UserStatus.REJECTED:
            return templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "error": "تم رفض حسابك. يرجى التواصل مع الإدارة.",
                    "form_data": form_data
                },
                status_code=403
            )
        elif not user.is_active:
            return templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "error": "حسابك غير نشط. يرجى التواصل مع الإدارة.",
                    "form_data": form_data
                },
                status_code=403
            )
    else:
        # For admin users, only check if account is active (ignore approval status)
        if not user.is_active:
            return templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "error": "حساب الإدارة غير نشط. يرجى التواصل مع مدير النظام.",
                    "form_data": form_data
                },
                status_code=403
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
    # Check if request is over HTTPS (considering reverse proxy)
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    is_https = forwarded_proto == "https" or request.url.scheme == "https"

    # Enhanced mobile-friendly cookie settings
    user_agent = request.headers.get("User-Agent", "").lower()
    is_mobile = any(mobile_indicator in user_agent for mobile_indicator in
                   ['mobile', 'android', 'iphone', 'ipad', 'tablet'])

    # Log cookie setting for debugging
    logger.info(f"Setting cookie for user {user.username} - Mobile: {is_mobile}, HTTPS: {is_https}")

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        secure=is_https,  # Set to True for HTTPS connections
        samesite="lax",  # Lax is better for mobile compatibility than strict
        path="/"  # Ensure cookie is available for all paths
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
    # Preserve form data for potential re-display
    form_data = {
        "username": username,
        "email": email,
        "full_name": full_name
        # Note: We don't preserve passwords for security reasons
    }

    # Validate password confirmation
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "كلمات المرور غير متطابقة",
                "form_data": form_data
            },
            status_code=400
        )

    # Validate password strength
    if len(password) < 6:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل",
                "form_data": form_data
            },
            status_code=400
        )

    # Validate username format
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "اسم المستخدم يجب أن يحتوي على أحرف وأرقام وشرطة سفلية فقط",
                "form_data": form_data
            },
            status_code=400
        )

    if len(username) < 3 or len(username) > 20:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "اسم المستخدم يجب أن يكون بين 3 و 20 حرف",
                "form_data": form_data
            },
            status_code=400
        )

    # Validate email format
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "صيغة البريد الإلكتروني غير صحيحة",
                "form_data": form_data
            },
            status_code=400
        )

    # Validate full name
    if len(full_name.strip()) < 2:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": "الاسم الكامل يجب أن يكون حرفين على الأقل",
                "form_data": form_data
            },
            status_code=400
        )

    try:
        # Create user
        user = UserService.create_user(
            db=db,
            username=username,
            email=email,
            full_name=full_name.strip(),
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
                "success": "تم إنشاء الحساب بنجاح! حسابك في انتظار موافقة الإدارة. ستتمكن من تسجيل الدخول بمجرد الموافقة على حسابك."
            }
        )

    except HTTPException as e:
        # Translate common error messages to Arabic
        error_message = e.detail
        if "Username already registered" in error_message:
            error_message = "اسم المستخدم مُستخدم بالفعل"
        elif "Email already registered" in error_message:
            error_message = "البريد الإلكتروني مُستخدم بالفعل"

        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error": error_message,
                "form_data": form_data
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
