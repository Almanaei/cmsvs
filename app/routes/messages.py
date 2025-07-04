"""
Message routes for user-to-user messaging functionality
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.services.message_service import MessageService
from app.utils.auth import verify_token
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


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

    from app.services.user_service import UserService
    user = UserService.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=403, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    return user


# Pydantic models for request/response
class MessageCreate(BaseModel):
    recipient_id: int
    subject: str
    content: str


class MessageResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


# HTML Pages
@router.get("/messages", response_class=HTMLResponse)
async def messages_page(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Messages inbox page"""
    # Get inbox messages
    inbox_data = MessageService.get_user_inbox(db, current_user.id, page=1, per_page=10)
    
    # Get available recipients
    recipients = MessageService.get_available_recipients(db, current_user.id)
    
    return templates.TemplateResponse(
        "messages/inbox.html",
        {
            "request": request,
            "current_user": current_user,
            "messages": inbox_data["messages"],
            "unread_count": inbox_data["unread_count"],
            "recipients": recipients,
            "page_title": "صندوق الرسائل"
        }
    )


@router.get("/messages/sent", response_class=HTMLResponse)
async def sent_messages_page(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Sent messages page"""
    sent_data = MessageService.get_user_sent_messages(db, current_user.id, page=1, per_page=10)
    
    return templates.TemplateResponse(
        "messages/sent.html",
        {
            "request": request,
            "current_user": current_user,
            "messages": sent_data["messages"],
            "page_title": "الرسائل المرسلة"
        }
    )


@router.get("/messages/compose", response_class=HTMLResponse)
async def compose_message_page(
    request: Request,
    recipient_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Compose new message page"""
    recipients = MessageService.get_available_recipients(db, current_user.id)
    
    # Get recipient info if specified
    selected_recipient = None
    if recipient_id:
        selected_recipient = db.query(User).filter(User.id == recipient_id).first()
    
    return templates.TemplateResponse(
        "messages/compose.html",
        {
            "request": request,
            "current_user": current_user,
            "recipients": recipients,
            "selected_recipient": selected_recipient,
            "page_title": "إنشاء رسالة جديدة"
        }
    )


@router.get("/messages/{message_id}", response_class=HTMLResponse)
async def view_message_page(
    request: Request,
    message_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """View specific message page"""
    message = MessageService.get_message_by_id(db, message_id, current_user.id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Mark as read if user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        MessageService.mark_message_as_read(db, message_id, current_user.id)
    
    return templates.TemplateResponse(
        "messages/view.html",
        {
            "request": request,
            "current_user": current_user,
            "message": message.to_dict(current_user.id),
            "page_title": f"رسالة: {message.subject}"
        }
    )


# API Endpoints
@router.post("/api/messages", response_model=MessageResponse)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Send a new message"""
    try:
        # Validate input
        if not message_data.subject.strip():
            raise ValueError("Subject is required")
        
        if not message_data.content.strip():
            raise ValueError("Message content is required")
        
        if message_data.recipient_id == current_user.id:
            raise ValueError("Cannot send message to yourself")
        
        # Send message
        message = MessageService.send_message(
            db=db,
            sender_id=current_user.id,
            recipient_id=message_data.recipient_id,
            subject=message_data.subject,
            content=message_data.content
        )
        
        return MessageResponse(
            success=True,
            message="تم إرسال الرسالة بنجاح",
            data=message.to_dict(current_user.id)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء إرسال الرسالة")


@router.get("/api/messages/inbox")
async def get_inbox_messages(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    include_read: bool = Query(True),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get inbox messages API"""
    inbox_data = MessageService.get_user_inbox(
        db=db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        include_read=include_read
    )
    
    return inbox_data


@router.get("/api/messages/sent")
async def get_sent_messages(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get sent messages API"""
    sent_data = MessageService.get_user_sent_messages(
        db=db,
        user_id=current_user.id,
        page=page,
        per_page=per_page
    )
    
    return sent_data


@router.put("/api/messages/{message_id}/read")
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Mark message as read"""
    success = MessageService.mark_message_as_read(db, message_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"success": True, "message": "تم تحديد الرسالة كمقروءة"}


@router.delete("/api/messages/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Delete message"""
    success = MessageService.delete_message(db, message_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"success": True, "message": "تم حذف الرسالة"}


@router.get("/api/messages/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get unread messages count"""
    count = MessageService.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.get("/api/users/recipients")
async def get_available_recipients(
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get list of available message recipients"""
    recipients = MessageService.get_available_recipients(db, current_user.id)
    return {"recipients": recipients}
