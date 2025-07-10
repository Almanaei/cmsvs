from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from app.database import get_db
from app.models.user import User, UserRole
from app.models.notification import NotificationType, NotificationPriority
from app.services.notification_service import NotificationService
from app.services.push_service import PushService
from app.utils.auth import verify_token
from app.services.user_service import UserService
from pydantic import BaseModel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


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


async def require_admin_cookie(request: Request, db: Session = Depends(get_db)) -> User:
    """Require admin user using cookie authentication"""
    user = await get_current_user_cookie(request, db)

    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return user


class PushSubscriptionData(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    device_name: Optional[str] = None


class NotificationPreferencesData(BaseModel):
    push_notifications_enabled: bool = True
    in_app_notifications_enabled: bool = True
    email_notifications_enabled: bool = False
    request_status_notifications: bool = True
    request_updates_notifications: bool = True
    admin_message_notifications: bool = True
    system_announcement_notifications: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(
    request: Request,
    page: int = Query(1, ge=1),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """User notifications page"""
    try:
        # Get user notifications
        notifications_data = NotificationService.get_user_notifications(
            db=db,
            user_id=current_user.id,
            page=page,
            per_page=20,
            unread_only=unread_only
        )
        
        # Get unread count
        unread_count = NotificationService.get_unread_count(db, current_user.id)
        
        return templates.TemplateResponse(
            "notifications/list.html",
            {
                "request": request,
                "current_user": current_user,
                "notifications": notifications_data["notifications"],
                "total_count": notifications_data["total_count"],
                "page": page,
                "total_pages": notifications_data["total_pages"],
                "unread_only": unread_only,
                "unread_count": unread_count
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading notifications page: {str(e)}")
        return templates.TemplateResponse(
            "errors/500.html",
            {"request": request, "current_user": current_user},
            status_code=500
        )


@router.get("/api/notifications", response_class=JSONResponse)
async def get_notifications_api(
    page: int = Query(1, ge=1),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get user notifications via API"""
    try:
        notifications_data = NotificationService.get_user_notifications(
            db=db,
            user_id=current_user.id,
            page=page,
            per_page=20,
            unread_only=unread_only
        )
        
        # Convert notifications to dict format
        notifications_list = []
        for notification in notifications_data["notifications"]:
            notifications_list.append({
                "id": notification.id,
                "type": notification.type.value,
                "priority": notification.priority.value,
                "title": notification.title,
                "message": notification.message,
                "action_url": notification.action_url,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat() if notification.created_at else None,
                "read_at": notification.read_at.isoformat() if notification.read_at else None,
                "extra_data": notification.extra_data
            })
        
        return JSONResponse({
            "success": True,
            "notifications": notifications_list,
            "total_count": notifications_data["total_count"],
            "page": page,
            "total_pages": notifications_data["total_pages"],
            "unread_count": NotificationService.get_unread_count(db, current_user.id)
        })
        
    except Exception as e:
        logger.error(f"Error getting notifications via API: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "Failed to load notifications"
        }, status_code=500)


@router.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    try:
        success = NotificationService.mark_notification_as_read(
            db=db,
            notification_id=notification_id,
            user_id=current_user.id
        )
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Notification marked as read"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Notification not found or already read"
            }, status_code=404)
            
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "Failed to mark notification as read"
        }, status_code=500)


@router.post("/api/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    try:
        updated_count = NotificationService.mark_all_notifications_as_read(
            db=db,
            user_id=current_user.id
        )
        
        return JSONResponse({
            "success": True,
            "message": f"Marked {updated_count} notifications as read",
            "updated_count": updated_count
        })
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "Failed to mark notifications as read"
        }, status_code=500)


@router.get("/api/notifications/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get unread notifications count"""
    try:
        unread_count = NotificationService.get_unread_count(db, current_user.id)
        
        return JSONResponse({
            "success": True,
            "unread_count": unread_count
        })
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "Failed to get unread count"
        }, status_code=500)


@router.post("/api/push/subscribe")
async def subscribe_to_push(
    subscription_data: PushSubscriptionData,
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Subscribe user to push notifications"""
    try:
        user_agent = request.headers.get("user-agent", "")
        
        subscription = PushService.subscribe_user(
            db=db,
            user_id=current_user.id,
            endpoint=subscription_data.endpoint,
            p256dh_key=subscription_data.p256dh,
            auth_key=subscription_data.auth,
            user_agent=user_agent,
            device_name=subscription_data.device_name
        )
        
        return JSONResponse({
            "success": True,
            "message": "Successfully subscribed to push notifications",
            "subscription_id": subscription.id
        })
        
    except Exception as e:
        logger.error(f"Error subscribing to push notifications: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "Failed to subscribe to push notifications"
        }, status_code=500)


@router.post("/api/push/unsubscribe")
async def unsubscribe_from_push(
    endpoint: Optional[str] = None,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Unsubscribe user from push notifications"""
    try:
        success = PushService.unsubscribe_user(
            db=db,
            user_id=current_user.id,
            endpoint=endpoint
        )
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Successfully unsubscribed from push notifications"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to unsubscribe"
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"Error unsubscribing from push notifications: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "Failed to unsubscribe from push notifications"
        }, status_code=500)


@router.get("/notifications/preferences", response_class=HTMLResponse)
async def notification_preferences_page(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Notification preferences page"""
    try:
        preferences = PushService.get_notification_preferences(db, current_user.id)
        subscriptions = PushService.get_user_subscriptions(db, current_user.id)
        
        return templates.TemplateResponse(
            "notifications/preferences.html",
            {
                "request": request,
                "current_user": current_user,
                "preferences": preferences,
                "subscriptions": subscriptions
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading notification preferences: {str(e)}")
        return templates.TemplateResponse(
            "errors/500.html",
            {"request": request, "current_user": current_user},
            status_code=500
        )


@router.post("/api/notifications/preferences")
async def update_notification_preferences(
    preferences_data: NotificationPreferencesData,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Update notification preferences"""
    try:
        preferences = PushService.update_notification_preferences(
            db=db,
            user_id=current_user.id,
            preferences=preferences_data.dict()
        )
        
        if preferences:
            return JSONResponse({
                "success": True,
                "message": "Notification preferences updated successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to update preferences"
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"Error updating notification preferences: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "Failed to update notification preferences"
        }, status_code=500)
