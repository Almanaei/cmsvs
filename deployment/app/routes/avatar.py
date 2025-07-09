import time
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.user_service import UserService
from app.services.avatar_service import AvatarService
from app.routes.admin import require_admin_cookie
from app.utils.auth import verify_token
from app.models.user import User

router = APIRouter()


async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user from cookie authentication"""
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

    return user


@router.post("/upload/{user_id}")
async def upload_avatar(
    user_id: int,
    request: Request,
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Upload avatar for a user"""
    try:
        # Check permissions:
        # - ADMIN/MANAGER: can update any user's avatar
        # - Regular users: can only update their own avatar

        # Convert role to string for comparison
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

        if user_role not in ['admin', 'manager'] and current_user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="غير مسموح لك بتعديل صورة هذا المستخدم. يمكنك فقط تعديل صورتك الشخصية."
            )
        
        # Get user
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete old avatar if exists
        AvatarService.delete_avatar(user_id, db)

        # Upload new avatar
        avatar_url = await AvatarService.upload_avatar(avatar, user_id, db)
        
        # Redirect back to appropriate page based on user role
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

        if user_role in ['admin', 'manager']:
            redirect_url = f"/admin/users/{user_id}/edit?avatar_updated=true&t={int(time.time())}"
        else:
            redirect_url = f"/profile?avatar_updated=true&t={int(time.time())}"

        return RedirectResponse(url=redirect_url, status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")


@router.get("/delete/{user_id}")
async def delete_avatar(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """Delete avatar for a user"""
    try:
        # Check permissions:
        # - ADMIN/MANAGER: can delete any user's avatar
        # - Regular users: can only delete their own avatar

        # Convert role to string for comparison
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

        if user_role not in ['admin', 'manager'] and current_user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="غير مسموح لك بحذف صورة هذا المستخدم. يمكنك فقط حذف صورتك الشخصية."
            )
        
        # Get user
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete avatar file and database record
        AvatarService.delete_avatar(user_id, db)
        
        # Redirect back to appropriate page based on user role
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

        if user_role in ['admin', 'manager']:
            redirect_url = f"/admin/users/{user_id}/edit?avatar_deleted=true"
        else:
            redirect_url = f"/profile?avatar_deleted=true"

        return RedirectResponse(url=redirect_url, status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete avatar: {str(e)}")


@router.get("/default/{user_id}")
async def get_default_avatar(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get default avatar URL for a user"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    default_url = AvatarService.generate_default_avatar_url(user_id, user.full_name)
    return {"avatar_url": default_url}
