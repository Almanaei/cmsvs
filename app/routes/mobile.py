from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.database import get_db
from app.utils.auth import verify_token
from app.models.user import User
from app.services.user_service import UserService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# Pydantic models for mobile API
class MobileTokenRequest(BaseModel):
    token: str
    platform: str  # 'android' or 'ios'
    device_info: Optional[dict] = None

class MobileTokenResponse(BaseModel):
    success: bool
    message: str

class AppConfigResponse(BaseModel):
    app_name: str
    app_version: str
    api_base_url: str
    features: dict

@router.post("/register-token", response_model=MobileTokenResponse)
async def register_push_token(
    request: MobileTokenRequest,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Register a push notification token for a mobile device"""
    try:
        user_service = UserService(db)
        
        # Store the push token in user's profile or a separate table
        # For now, we'll store it in the user's profile as a JSON field
        user_data = {
            "push_token": request.token,
            "platform": request.platform,
            "device_info": request.device_info or {}
        }
        
        # Update user's mobile settings
        success = user_service.update_user_mobile_settings(current_user.id, user_data)
        
        if success:
            logger.info(f"Push token registered for user {current_user.id} on {request.platform}")
            return MobileTokenResponse(
                success=True,
                message="Push token registered successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to register push token")
            
    except Exception as e:
        logger.error(f"Error registering push token: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/config", response_model=AppConfigResponse)
async def get_mobile_app_config(
    current_user: User = Depends(verify_token)
):
    """Get mobile app configuration"""
    try:
        config = AppConfigResponse(
            app_name="إرشيف - الدفاع المدني",
            app_version="1.0.0",
            api_base_url="https://www.webtado.live",
            features={
                "push_notifications": True,
                "camera": True,
                "offline_mode": True,
                "file_upload": True,
                "biometric_auth": False  # Can be enabled later
            }
        )
        
        return config
        
    except Exception as e:
        logger.error(f"Error getting mobile config: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/sync-offline-data")
async def sync_offline_data(
    request: Request,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Sync offline data when connection is restored"""
    try:
        data = await request.json()
        offline_actions = data.get("actions", [])
        
        results = []
        
        for action in offline_actions:
            try:
                # Process each offline action
                # This is a simplified example - you'd implement actual sync logic
                action_type = action.get("type")
                action_data = action.get("data")
                
                if action_type == "create_request":
                    # Handle offline request creation
                    result = await handle_offline_request_creation(action_data, current_user, db)
                    results.append({"action_id": action.get("id"), "success": True, "result": result})
                elif action_type == "update_request":
                    # Handle offline request update
                    result = await handle_offline_request_update(action_data, current_user, db)
                    results.append({"action_id": action.get("id"), "success": True, "result": result})
                else:
                    results.append({"action_id": action.get("id"), "success": False, "error": "Unknown action type"})
                    
            except Exception as e:
                logger.error(f"Error processing offline action: {str(e)}")
                results.append({"action_id": action.get("id"), "success": False, "error": str(e)})
        
        return JSONResponse(content={
            "success": True,
            "synced_actions": len([r for r in results if r["success"]]),
            "failed_actions": len([r for r in results if not r["success"]]),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error syncing offline data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def mobile_health_check():
    """Health check endpoint for mobile app"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "mobile-api",
        "timestamp": "2024-01-01T00:00:00Z"
    })

@router.post("/feedback")
async def submit_mobile_feedback(
    request: Request,
    current_user: User = Depends(verify_token)
):
    """Submit feedback from mobile app"""
    try:
        data = await request.json()
        feedback_text = data.get("feedback", "")
        app_version = data.get("app_version", "")
        platform = data.get("platform", "")
        
        # Log the feedback (you could also store it in database)
        logger.info(f"Mobile feedback from user {current_user.id}: {feedback_text}")
        
        return JSONResponse(content={
            "success": True,
            "message": "شكراً لك على ملاحظاتك"
        })
        
    except Exception as e:
        logger.error(f"Error submitting mobile feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Helper functions for offline sync
async def handle_offline_request_creation(data, user, db):
    """Handle creation of requests that were made offline"""
    # Implement your request creation logic here
    # This is a placeholder
    return {"id": "new_request_id", "status": "created"}

async def handle_offline_request_update(data, user, db):
    """Handle updates to requests that were made offline"""
    # Implement your request update logic here
    # This is a placeholder
    return {"id": data.get("request_id"), "status": "updated"}
