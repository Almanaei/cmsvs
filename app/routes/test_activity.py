"""
Test routes for activity logging functionality
"""
from fastapi import APIRouter, Depends, Request, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from app.database import get_db
from app.models.user import User, UserRole
from app.models.request import Request as RequestModel
from app.models.activity import Activity, ActivityType
from app.services.user_service import UserService
from app.services.request_service import RequestService
from app.services.activity_service import ActivityService
from app.utils.auth import get_current_user_cookie
from app.utils.request_utils import log_cross_user_activity, log_user_activity


router = APIRouter()
from app.utils.templates import templates
logger = logging.getLogger(__name__)


@router.get("/test/activity", response_class=HTMLResponse)
async def test_activity_page(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Test page for activity logging functionality"""
    
    # Get all users for testing
    all_users = UserService.get_all_users(db, limit=100)
    
    # Get all requests for testing
    all_requests = RequestService.get_all_requests(db, limit=100)
    
    # Get recent activities for current user
    user_activities = ActivityService.get_user_activities(db, current_user.id, limit=20)
    
    # Get all activity types
    activity_types = [activity_type.value for activity_type in ActivityType]
    
    return templates.TemplateResponse(
        "test/activity_test.html",
        {
            "request": request,
            "current_user": current_user,
            "all_users": all_users,
            "all_requests": all_requests,
            "user_activities": user_activities,
            "activity_types": activity_types
        }
    )


@router.post("/test/activity/log-cross-user")
async def test_log_cross_user_activity(
    request: Request,
    target_user_id: int = Form(...),
    activity_type: str = Form(...),
    description: str = Form(...),
    request_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Test endpoint to manually log cross-user activity"""
    try:
        # Get target user
        target_user = UserService.get_user_by_id(db, target_user_id)
        if not target_user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Target user not found"}
            )
        
        # Prepare details
        details = {
            "test_activity": True,
            "manual_log": True
        }
        
        if request_id:
            req = RequestService.get_request_by_id(db, request_id)
            if req:
                details.update({
                    "request_id": req.id,
                    "request_number": req.request_number
                })
        
        # Log the activity
        success = log_cross_user_activity(
            db=db,
            request_owner_id=target_user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type=activity_type,
            description=description,
            request=request,
            details=details
        )
        
        if success:
            return JSONResponse({
                "success": True,
                "message": f"Activity logged successfully for user {target_user.full_name}"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to log activity"
            })
            
    except Exception as e:
        logger.error(f"Error in test activity logging: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Error: {str(e)}"
        })


@router.post("/test/activity/log-regular")
async def test_log_regular_activity(
    request: Request,
    activity_type: str = Form(...),
    description: str = Form(...),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Test endpoint to manually log regular user activity"""
    try:
        details = {
            "test_activity": True,
            "manual_log": True,
            "regular_activity": True
        }
        
        # Log the activity
        success = log_user_activity(
            db=db,
            user_id=current_user.id,
            activity_type=activity_type,
            description=description,
            request=request,
            details=details
        )
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Regular activity logged successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to log activity"
            })
            
    except Exception as e:
        logger.error(f"Error in test regular activity logging: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Error: {str(e)}"
        })


@router.get("/test/activity/user/{user_id}")
async def get_user_activities_test(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get activities for a specific user (for testing)"""
    try:
        # Get target user
        target_user = UserService.get_user_by_id(db, user_id)
        if not target_user:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        # Get activities
        activities = ActivityService.get_user_activities(db, user_id, limit=limit)
        
        # Format activities for JSON response
        formatted_activities = []
        for activity in activities:
            formatted_activity = {
                "id": activity.get("id"),
                "activity_type": activity.get("activity_type"),
                "description": activity.get("description"),
                "created_at": activity.get("created_at"),
                "details": activity.get("details", {}),
                "ip_address": activity.get("ip_address"),
                "user_agent": activity.get("user_agent")
            }
            formatted_activities.append(formatted_activity)
        
        return JSONResponse({
            "success": True,
            "user": {
                "id": target_user.id,
                "username": target_user.username,
                "full_name": target_user.full_name
            },
            "activities": formatted_activities,
            "total_count": len(formatted_activities)
        })
        
    except Exception as e:
        logger.error(f"Error getting user activities: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Error: {str(e)}"
        })


@router.get("/test/password-toggle", response_class=HTMLResponse)
async def password_toggle_demo(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Demo page for password toggle functionality"""
    return templates.TemplateResponse(
        "test/password_toggle_demo.html",
        {
            "request": request,
            "current_user": current_user
        }
    )


@router.get("/test/user-requests/{user_id}")
async def test_user_requests_data(
    user_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Test endpoint to check user requests data fetching"""
    try:
        # Get the target user
        target_user = UserService.get_user_by_id(db, user_id)
        if not target_user:
            return JSONResponse({
                "success": False,
                "error": "User not found"
            })

        # Get user's requests
        user_requests = RequestService.get_requests_by_user_id(
            db,
            user_id=user_id,
            limit=100
        )

        # Get user's request statistics
        user_request_stats = RequestService.get_user_request_statistics(db, user_id)

        # Format requests for JSON response
        formatted_requests = []
        for req in user_requests:
            formatted_requests.append({
                "id": req.id,
                "request_number": req.request_number,
                "unique_code": req.unique_code,
                "status": req.status.value,
                "full_name": req.full_name,
                "personal_number": req.personal_number,
                "building_name": req.building_name,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "files_count": len(req.files) if req.files else 0
            })

        return JSONResponse({
            "success": True,
            "target_user": {
                "id": target_user.id,
                "username": target_user.username,
                "full_name": target_user.full_name,
                "role": target_user.role.value
            },
            "requests_count": len(user_requests),
            "requests": formatted_requests,
            "statistics": user_request_stats
        })

    except Exception as e:
        logger.error(f"Error testing user requests data: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Error: {str(e)}"
        })


@router.get("/test/activity/simulate-cross-user/{request_id}")
async def simulate_cross_user_access(
    request_id: int,
    action: str = Query("view", description="Action to simulate: view, edit, status_update, file_access"),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Simulate cross-user request access for testing"""
    try:
        # Get the request
        req = RequestService.get_request_by_id(db, request_id)
        if not req:
            return JSONResponse(
                status_code=404,
                content={"error": "Request not found"}
            )
        
        # Check if this is actually cross-user access
        is_cross_user = req.user_id != current_user.id
        
        # Simulate different actions
        activity_mapping = {
            "view": {
                "type": "cross_user_request_viewed",
                "description": f"تم عرض الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username} (محاكاة)"
            },
            "edit": {
                "type": "cross_user_request_edited", 
                "description": f"تم تعديل الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username} (محاكاة)"
            },
            "status_update": {
                "type": "cross_user_request_status_updated",
                "description": f"تم تحديث حالة الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username} (محاكاة)"
            },
            "file_access": {
                "type": "cross_user_file_accessed",
                "description": f"تم الوصول إلى ملفات الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username} (محاكاة)"
            }
        }
        
        if action not in activity_mapping:
            return JSONResponse({
                "success": False,
                "error": f"Invalid action. Available actions: {list(activity_mapping.keys())}"
            })
        
        activity_info = activity_mapping[action]
        
        if is_cross_user:
            # Log cross-user activity
            from fastapi import Request as FastAPIRequest
            fake_request = FastAPIRequest(scope={"type": "http", "method": "GET", "headers": []})
            
            success = log_cross_user_activity(
                db=db,
                request_owner_id=req.user_id,
                accessing_user_id=current_user.id,
                accessing_user_name=current_user.full_name or current_user.username,
                activity_type=activity_info["type"],
                description=activity_info["description"],
                request=fake_request,
                details={
                    "request_id": req.id,
                    "request_number": req.request_number,
                    "simulated_action": action,
                    "test_simulation": True
                }
            )
            
            return JSONResponse({
                "success": success,
                "message": f"Simulated {action} action on request {req.request_number}",
                "is_cross_user": True,
                "request_owner_id": req.user_id,
                "accessing_user_id": current_user.id
            })
        else:
            return JSONResponse({
                "success": True,
                "message": f"This is your own request - no cross-user activity to log",
                "is_cross_user": False,
                "request_owner_id": req.user_id,
                "accessing_user_id": current_user.id
            })
            
    except Exception as e:
        logger.error(f"Error simulating cross-user access: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Error: {str(e)}"
        })
