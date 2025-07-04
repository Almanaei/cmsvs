from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import get_db
from app.utils.auth import verify_token
from app.models.user import User
from app.services.user_service import UserService
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
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


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Settings page for user preferences and account management"""
    try:
        # Get user's current settings/preferences
        user_data = {
            "full_name": current_user.full_name,
            "email": current_user.email,
            "username": current_user.username,
            "role": current_user.role.value,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at
        }
        
        # Get user statistics
        user_stats = UserService.get_user_statistics(db, current_user.id)
        
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "current_user": current_user,
                "user_data": user_data,
                "user_stats": user_stats,
                "app_settings": {
                    "app_name": settings.app_name,
                    "app_version": settings.app_version,
                    "max_file_size": settings.max_file_size,
                    "allowed_file_types": settings.allowed_file_types_list
                }
            }
        )
    except Exception as e:
        logger.error(f"Error loading settings page: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/settings/profile")
async def update_profile_settings(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Update user profile settings"""
    try:
        # Update user profile
        updated_user = UserService.update_user_profile(
            db=db,
            user_id=current_user.id,
            full_name=full_name,
            email=email
        )
        
        if updated_user:
            logger.info(f"User {current_user.id} updated profile settings")
            return RedirectResponse(url="/settings?success=profile_updated", status_code=303)
        else:
            return RedirectResponse(url="/settings?error=update_failed", status_code=303)
            
    except Exception as e:
        logger.error(f"Error updating profile settings: {str(e)}")
        return RedirectResponse(url="/settings?error=server_error", status_code=303)


@router.post("/settings/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        # Validate new password confirmation
        if new_password != confirm_password:
            return RedirectResponse(url="/settings?error=password_mismatch", status_code=303)
        
        # Validate password length
        if len(new_password) < 6:
            return RedirectResponse(url="/settings?error=password_too_short", status_code=303)
        
        # Change password
        success = UserService.change_password(
            db=db,
            user_id=current_user.id,
            current_password=current_password,
            new_password=new_password
        )
        
        if success:
            logger.info(f"User {current_user.id} changed password")
            return RedirectResponse(url="/settings?success=password_changed", status_code=303)
        else:
            return RedirectResponse(url="/settings?error=invalid_current_password", status_code=303)
            
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return RedirectResponse(url="/settings?error=server_error", status_code=303)


@router.post("/settings/preferences")
async def update_preferences(
    request: Request,
    notifications_enabled: Optional[str] = Form(None),
    email_notifications: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Update user preferences (placeholder for future implementation)"""
    try:
        # Convert form checkboxes to boolean
        notifications_enabled = notifications_enabled == "on"
        email_notifications = email_notifications == "on"
        
        # TODO: Implement user preferences storage
        # For now, just redirect with success
        logger.info(f"User {current_user.id} updated preferences")
        return RedirectResponse(url="/settings?success=preferences_updated", status_code=303)
        
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        return RedirectResponse(url="/settings?error=server_error", status_code=303)
