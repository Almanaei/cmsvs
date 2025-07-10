from fastapi import APIRouter, Depends, Request, Form, UploadFile, File as FastAPIFile, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, RedirectResponse

from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import threading
import os
import csv
import io
import logging
from datetime import datetime
from app.database import get_db, engine
from app.utils.auth import verify_token
from sqlalchemy import text
from app.services.user_service import UserService
from app.services.request_service import RequestService
from app.services.avatar_service import AvatarService
from app.services.activity_service import ActivityService
from app.models.user import User, UserRole
from app.models.request import RequestStatus
from app.models.activity import ActivityType
from app.models.file import File
from app.config import settings

router = APIRouter()
from app.utils.templates import templates

# Initialize logger
logger = logging.getLogger(__name__)

@router.get("/test-dropdown", response_class=HTMLResponse)
async def test_dropdown(request: Request):
    """Test page for dropdown functionality"""
    return templates.TemplateResponse("test_dropdown.html", {"request": request})







# Thread-safe request ID generation
_request_id_lock = threading.Lock()
_request_id_counter = 0

def generate_unique_request_number():
    """Generate a thread-safe unique request number that will be used in database"""
    global _request_id_counter

    with _request_id_lock:
        # Get current timestamp
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S")

        # Increment counter for uniqueness within the same second
        _request_id_counter += 1

        # Reset counter if it gets too large (prevent overflow)
        if _request_id_counter > 9999:
            _request_id_counter = 1

        # Generate request number with counter for uniqueness
        # This will be the actual request_number stored in database
        request_number = f"REQ-{timestamp}-{_request_id_counter:04d}"

        return {
            "request_number": request_number,
            "timestamp": timestamp,
            "counter": _request_id_counter
        }


async def get_current_user_cookie(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user using cookie authentication with enhanced mobile debugging and fallback"""
    user_agent = request.headers.get("User-Agent", "")
    client_ip = request.client.host if request.client else "unknown"
    is_mobile = any(mobile_indicator in user_agent.lower() for mobile_indicator in
                   ['mobile', 'android', 'iphone', 'ipad', 'tablet'])

    token = request.cookies.get("access_token")

    # Mobile fallback: check for token in headers if cookie is missing
    if not token and is_mobile:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header
            logger.info(f"Using Authorization header for mobile - IP: {client_ip}")

    if not token:
        logger.warning(f"No access token found - IP: {client_ip}, Mobile: {is_mobile}, "
                      f"Cookies: {list(request.cookies.keys())}, "
                      f"Auth Header: {'Yes' if request.headers.get('Authorization') else 'No'}")
        raise HTTPException(status_code=403, detail="Not authenticated")

    # Remove 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    payload = verify_token(token)
    if not payload:
        logger.warning(f"Invalid token - IP: {client_ip}, Mobile: {is_mobile}, "
                      f"Token length: {len(token) if token else 0}")
        raise HTTPException(status_code=403, detail="Invalid token")

    username = payload.get("sub")
    if not username:
        logger.warning(f"No username in token payload - IP: {client_ip}, Mobile: {is_mobile}")
        raise HTTPException(status_code=403, detail="Invalid token")

    user = UserService.get_user_by_username(db, username)
    if not user:
        logger.warning(f"User not found: {username} - IP: {client_ip}, Mobile: {is_mobile}")
        raise HTTPException(status_code=403, detail="User not found")

    if not user.is_active:
        logger.warning(f"Inactive user: {username} - IP: {client_ip}, Mobile: {is_mobile}")
        raise HTTPException(status_code=403, detail="Inactive user")

    logger.debug(f"Authentication successful - User: {username}, Mobile: {is_mobile}, IP: {client_ip}")
    return user


@router.get("/debug/user-role", response_class=HTMLResponse)
async def debug_user_role(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check user role detection"""
    user_agent = request.headers.get("User-Agent", "")
    is_mobile = any(mobile_indicator in user_agent.lower() for mobile_indicator in
                   ['mobile', 'android', 'iphone', 'ipad', 'tablet'])

    debug_info = {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.value,
        "is_admin": current_user.role == UserRole.ADMIN,
        "is_mobile": is_mobile,
        "user_agent": user_agent,
        "role_enum": str(current_user.role),
        "admin_enum": str(UserRole.ADMIN)
    }

    return JSONResponse(debug_info)


@router.get("/debug/mobile-nav-test", response_class=HTMLResponse)
async def debug_mobile_nav_test(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Debug page for testing mobile navigation functionality"""
    return templates.TemplateResponse(
        "debug/mobile_nav_test.html",
        {
            "request": request,
            "current_user": current_user
        }
    )


@router.get("/debug/mobile-file-test", response_class=HTMLResponse)
async def debug_mobile_file_test(request: Request):
    """Debug page for testing mobile file management improvements"""
    return templates.TemplateResponse(
        "debug/mobile_file_test.html",
        {"request": request}
    )


@router.get("/debug/dropdown-test", response_class=HTMLResponse)
async def debug_dropdown_test(request: Request):
    """Debug page for testing dropdown text visibility fixes"""
    return templates.TemplateResponse(
        "debug/dropdown_test.html",
        {"request": request}
    )


@router.get("/debug/dropdown-debug", response_class=HTMLResponse)
async def debug_dropdown_debug(request: Request):
    """Comprehensive dropdown debug page for testing all scenarios"""
    return templates.TemplateResponse(
        "debug/dropdown_debug.html",
        {"request": request}
    )


@router.get("/debug/css-conflict-analyzer", response_class=HTMLResponse)
async def debug_css_conflict_analyzer(request: Request):
    """CSS conflict analyzer for dropdown styling issues"""
    return templates.TemplateResponse(
        "debug/css_conflict_analyzer.html",
        {"request": request}
    )


@router.get("/debug/dropdown-fix-verification", response_class=HTMLResponse)
async def debug_dropdown_fix_verification(request: Request):
    """Comprehensive verification of dropdown fixes"""
    return templates.TemplateResponse(
        "debug/dropdown_fix_verification.html",
        {"request": request}
    )


@router.get("/debug/mobile-request-view-test", response_class=HTMLResponse)
async def debug_mobile_request_view_test(request: Request):
    """Debug page for testing mobile request view improvements"""
    return templates.TemplateResponse(
        "debug/mobile_request_view_test.html",
        {"request": request}
    )


@router.get("/debug/mobile/{request_id}", response_class=HTMLResponse)
async def debug_mobile_request(
    request: Request,
    request_id: int,
    db: Session = Depends(get_db)
):
    """Debug endpoint for mobile request access issues"""
    user_agent = request.headers.get("User-Agent", "")
    client_ip = request.client.host if request.client else "unknown"
    is_mobile = any(mobile_indicator in user_agent.lower() for mobile_indicator in
                   ['mobile', 'android', 'iphone', 'ipad', 'tablet'])

    debug_info = {
        "request_id": request_id,
        "user_agent": user_agent,
        "client_ip": client_ip,
        "is_mobile": is_mobile,
        "cookies": dict(request.cookies),
        "headers": dict(request.headers),
        "url": str(request.url),
        "method": request.method
    }

    # Try to get current user
    try:
        current_user = await get_current_user_cookie(request, db)
        debug_info["current_user"] = {
            "id": current_user.id if current_user else None,
            "username": current_user.username if current_user else None,
            "role": current_user.role.value if current_user else None,
            "is_admin": current_user.role == UserRole.ADMIN if current_user else None
        }
    except Exception as e:
        debug_info["auth_error"] = str(e)
        debug_info["current_user"] = None

    # Try to get the request
    try:
        req = RequestService.get_request_by_id(db, request_id)
        debug_info["request_found"] = req is not None
        if req:
            debug_info["request_info"] = {
                "id": req.id,
                "user_id": req.user_id,
                "request_number": req.request_number,
                "status": req.status.value
            }
    except Exception as e:
        debug_info["request_error"] = str(e)
        debug_info["request_found"] = False

    logger.info(f"Mobile debug info: {debug_info}")

    return templates.TemplateResponse(
        "debug/mobile_debug.html",
        {
            "request": request,
            "debug_info": debug_info
        }
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """User dashboard"""
    # Get user's requests
    user_requests = RequestService.get_user_requests(db, current_user.id, limit=10)

    # Get recent activities
    activities = UserService.get_user_activities(db, current_user.id, limit=10)

    # Get request statistics for user
    total_requests = len(RequestService.get_user_requests(db, current_user.id, limit=1000))
    pending_requests = len([r for r in user_requests if r.status == RequestStatus.PENDING])
    completed_requests = len([r for r in user_requests if r.status == RequestStatus.COMPLETED])

    # Get user's personal progress data
    user_progress = RequestService.get_user_personal_progress(db, current_user.id)

    return templates.TemplateResponse(
        "dashboard/user_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "requests": user_requests,
            "activities": activities,
            "stats": {
                "total": total_requests,
                "pending": pending_requests,
                "completed": completed_requests
            },
            "user_progress": user_progress
        }
    )


@router.get("/dashboard/bento", response_class=HTMLResponse)
async def bento_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Bento-style dashboard with achievement integration"""
    # Import achievement service
    from app.services.achievement_service import AchievementService
    from app.models.achievement import UserStats

    # Initialize achievements if needed
    AchievementService.initialize_default_achievements(db)

    # Check if user is administrator or manager
    is_admin_or_manager = current_user.role in [UserRole.ADMIN, UserRole.MANAGER]

    if is_admin_or_manager:
        # For administrators, show leaderboard data instead of personal progress
        leaderboard_data = AchievementService.get_admin_leaderboard_data(db)

        # Get recent requests from all users for admin overview
        from app.models.request import Request as RequestModel
        all_requests = db.query(RequestModel).order_by(RequestModel.created_at.desc()).limit(5).all()

        # Get overall system stats
        total_requests = db.query(RequestModel).count()
        completed_requests = db.query(RequestModel).filter(RequestModel.status == RequestStatus.COMPLETED).count()
        pending_requests = db.query(RequestModel).filter(RequestModel.status == RequestStatus.PENDING).count()
        in_progress_requests = db.query(RequestModel).filter(RequestModel.status == RequestStatus.IN_PROGRESS).count()

        return templates.TemplateResponse(
            "dashboard/bento.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": all_requests,
                "stats": {
                    "total": total_requests,
                    "completed": completed_requests,
                    "pending": pending_requests,
                    "in_progress": in_progress_requests
                },
                "leaderboard_data": leaderboard_data,
                "is_admin": True,
                "user_progress": {},
                "achievement_data": {},
                "user_stats": {"total_points": 0, "global_rank": current_user.role.value.title(), "achievements_unlocked": 0}
            }
        )
    else:
        # For regular users, show personal achievement data
        # Sync user progress with actual request data
        AchievementService._sync_user_progress_with_requests(db, current_user.id)

        # Get user's requests
        user_requests = RequestService.get_user_requests(db, current_user.id, limit=10)

        # Get request statistics for user
        total_requests = len(RequestService.get_user_requests(db, current_user.id, limit=1000))
        pending_requests = len([r for r in user_requests if r.status == RequestStatus.PENDING])
        completed_requests = len([r for r in user_requests if r.status == RequestStatus.COMPLETED])

        # Get user's personal progress data
        user_progress = RequestService.get_user_personal_progress(db, current_user.id)

        # Get achievement data
        achievement_data = AchievementService.get_user_dashboard_data(db, current_user.id)

        # Get user stats
        user_stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
        if not user_stats:
            user_stats = UserStats(user_id=current_user.id)
            db.add(user_stats)
            db.commit()
            db.refresh(user_stats)

        return templates.TemplateResponse(
            "dashboard/bento.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": user_requests,
                "stats": {
                    "total": total_requests,
                    "pending": pending_requests,
                    "completed": completed_requests
                },
                "user_progress": user_progress,
                "achievement_data": {
                    "daily_progress": achievement_data.get("current_progress", {}).get("daily", {"target": 10, "current": 0, "percentage": 0, "status": "لم يبدأ"}),
                    "weekly_progress": achievement_data.get("current_progress", {}).get("weekly", {"target": 50, "current": 0, "percentage": 0, "status": "لم يبدأ"}),
                    "monthly_progress": achievement_data.get("current_progress", {}).get("monthly", {"target": 200, "current": 0, "percentage": 0, "status": "لم يبدأ"})
                },
                "is_admin": False,
                "leaderboard_data": {},
                "user_stats": user_stats
            }
        )


@router.get("/api/bento/stats", response_class=JSONResponse)
async def get_bento_stats(
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """API endpoint for bento dashboard statistics"""
    from app.services.achievement_service import AchievementService
    from app.models.achievement import UserStats

    # Check if user is administrator or manager
    is_admin_or_manager = current_user.role in [UserRole.ADMIN, UserRole.MANAGER]

    if is_admin_or_manager:
        # For administrators/managers, return leaderboard data
        leaderboard_data = AchievementService.get_admin_leaderboard_data(db)
        return {
            "is_admin": True,
            "leaderboard_data": leaderboard_data,
            "achievement_data": {},
            "user_progress": {}
        }

    # For regular users, sync progress and return personal data
    AchievementService._sync_user_progress_with_requests(db, current_user.id)

    # Get request statistics
    user_requests = RequestService.get_user_requests(db, current_user.id, limit=1000)
    total_requests = len(user_requests)
    pending_requests = len([r for r in user_requests if r.status == RequestStatus.PENDING])
    completed_requests = len([r for r in user_requests if r.status == RequestStatus.COMPLETED])

    # Get achievement data
    achievement_data = AchievementService.get_user_dashboard_data(db, current_user.id)

    # Get user stats
    user_stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    if not user_stats:
        user_stats = UserStats(user_id=current_user.id)
        db.add(user_stats)
        db.commit()
        db.refresh(user_stats)

    # Get user progress
    user_progress = RequestService.get_user_personal_progress(db, current_user.id)

    return {
        "stats": {
            "total": total_requests,
            "pending": pending_requests,
            "completed": completed_requests
        },
        "achievement_data": {
            "daily": achievement_data.get("current_progress", {}).get("daily", {"target": 10, "current": 0, "percentage": 0, "status": "لم يبدأ"}),
            "weekly": achievement_data.get("current_progress", {}).get("weekly", {"target": 50, "current": 0, "percentage": 0, "status": "لم يبدأ"}),
            "monthly": achievement_data.get("current_progress", {}).get("monthly", {"target": 200, "current": 0, "percentage": 0, "status": "لم يبدأ"})
        },
        "user_stats": {
            "total_points": user_stats.total_points,
            "global_rank": user_stats.global_rank,
            "daily_points": user_stats.daily_points,
            "weekly_points": user_stats.weekly_points,
            "monthly_points": user_stats.monthly_points
        },
        "user_progress": user_progress
    }


@router.get("/api/bento/recent-requests", response_class=JSONResponse)
async def get_recent_requests(
    limit: int = Query(5, le=20),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """API endpoint for recent requests data"""
    user_requests = RequestService.get_user_requests(db, current_user.id, limit=limit)

    requests_data = []
    for request in user_requests:
        requests_data.append({
            "id": request.id,
            "request_number": request.request_number,
            "title": request.title or "طلب جديد",
            "status": request.status.value,
            "created_at": request.created_at.strftime('%Y-%m-%d %H:%M'),
            "updated_at": request.updated_at.strftime('%Y-%m-%d %H:%M') if request.updated_at else None
        })

    return {
        "requests": requests_data,
        "total_count": len(requests_data)
    }


@router.get("/api/generate-request-number")
async def generate_request_number_endpoint(
    current_user: User = Depends(get_current_user_cookie)
):
    """Generate a unique request number that will be used in database and file naming"""
    try:
        request_info = generate_unique_request_number()
        return JSONResponse(content={
            "success": True,
            "request_number": request_info["request_number"],
            "timestamp": request_info["timestamp"],
            "message": "Request number generated successfully"
        })
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to generate request number"
            },
            status_code=500
        )


@router.get("/api/search-requests")
async def search_requests_api(
    q: str,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """API endpoint for quick search by unique code or other fields"""
    try:
        # Search in user's requests only (for regular users)
        if current_user.role == UserRole.ADMIN:
            results = RequestService.search_requests(db, q, limit=10)
        else:
            results = RequestService.search_requests(db, q, user_id=current_user.id, limit=10)

        # Format results for API response
        formatted_results = []
        for req in results:
            formatted_results.append({
                "id": req.id,
                "request_number": req.request_number,
                "unique_code": req.unique_code,
                "title": req.request_title,
                "building_permit_number": req.building_permit_number,
                "phone_number": req.phone_number,
                "full_name": req.full_name,
                "status": req.status.value,
                "created_at": req.created_at.strftime('%Y-%m-%d %H:%M'),
                "user_name": req.user.full_name if current_user.role == UserRole.ADMIN else None
            })

        return JSONResponse(content={
            "success": True,
            "results": formatted_results,
            "count": len(formatted_results)
        })
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": str(e),
                "message": "Search failed"
            },
            status_code=500
        )


@router.get("/requests/new", response_class=HTMLResponse)
async def new_request_form(
    request: Request,
    current_user: User = Depends(get_current_user_cookie)
):
    """Display new request form"""
    return templates.TemplateResponse(
        "requests/new_request.html",
        {
            "request": request,
            "current_user": current_user
        }
    )


# Achievement route moved to achievements.py


@router.post("/requests/new")
async def create_new_request(
    request: Request,
    # Pre-generated request number
    pre_generated_request_number: Optional[str] = Form(None),
    # Personal Information
    full_name: str = Form(...),
    personal_number: str = Form(...),
    phone_number: Optional[str] = Form(None),
    # Building Information
    building_name: Optional[str] = Form(None),
    road_name: Optional[str] = Form(None),
    building_number: Optional[str] = Form(None),
    civil_defense_file_number: Optional[str] = Form(None),
    building_permit_number: Optional[str] = Form(None),
    # License Sections
    licenses_section: bool = Form(False),
    fire_equipment_section: bool = Form(False),
    commercial_records_section: bool = Form(False),
    engineering_offices_section: bool = Form(False),
    hazardous_materials_section: bool = Form(False),
    # Required File Uploads
    architectural_plans: List[UploadFile] = FastAPIFile(None),
    electrical_mechanical_plans: List[UploadFile] = FastAPIFile(None),
    inspection_department: List[UploadFile] = FastAPIFile(None),
    # Optional File Uploads (conditional)
    fire_equipment_files: List[UploadFile] = FastAPIFile(None),
    commercial_records_files: List[UploadFile] = FastAPIFile(None),
    engineering_offices_files: List[UploadFile] = FastAPIFile(None),
    hazardous_materials_files: List[UploadFile] = FastAPIFile(None),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Create new civil defense request"""
    try:
        # Validate personal number (9 digits exactly)
        if not personal_number or len(personal_number) != 9 or not personal_number.isdigit():
            raise HTTPException(status_code=400, detail="الرقم الشخصي يجب أن يكون 9 أرقام بالضبط")

        # Validate required files
        if not architectural_plans or not architectural_plans[0].filename:
            raise HTTPException(status_code=400, detail="المخططات الهندسية المعمارية مطلوبة")

        if not electrical_mechanical_plans or not electrical_mechanical_plans[0].filename:
            raise HTTPException(status_code=400, detail="المخططات الهندسية الكهربائية والميكانيكية مطلوبة")

        if not inspection_department or not inspection_department[0].filename:
            raise HTTPException(status_code=400, detail="ملفات قسم التفتيش مطلوبة")

        # Create request with pre-generated request number if provided
        new_request = RequestService.create_request(
            db=db,
            user_id=current_user.id,
            full_name=full_name,
            personal_number=personal_number,
            phone_number=phone_number,
            building_name=building_name,
            road_name=road_name,
            building_number=building_number,
            civil_defense_file_number=civil_defense_file_number,
            building_permit_number=building_permit_number,
            licenses_section=licenses_section,
            fire_equipment_section=fire_equipment_section,
            commercial_records_section=commercial_records_section,
            engineering_offices_section=engineering_offices_section,
            hazardous_materials_section=hazardous_materials_section,
            pre_generated_request_number=pre_generated_request_number
        )

        # Prepare file categories
        file_categories = {
            "architectural_plans": architectural_plans if architectural_plans and architectural_plans[0].filename else [],
            "electrical_mechanical_plans": electrical_mechanical_plans if electrical_mechanical_plans and electrical_mechanical_plans[0].filename else [],
            "inspection_department": inspection_department if inspection_department and inspection_department[0].filename else []
        }

        # Add conditional file categories
        if fire_equipment_section and fire_equipment_files and fire_equipment_files[0].filename:
            file_categories["fire_equipment_files"] = fire_equipment_files

        if commercial_records_section and commercial_records_files and commercial_records_files[0].filename:
            file_categories["commercial_records_files"] = commercial_records_files

        if engineering_offices_section and engineering_offices_files and engineering_offices_files[0].filename:
            file_categories["engineering_offices_files"] = engineering_offices_files

        if hazardous_materials_section and hazardous_materials_files and hazardous_materials_files[0].filename:
            file_categories["hazardous_materials_files"] = hazardous_materials_files

        # Add all files to request with enhanced error handling
        upload_results = await RequestService.add_categorized_files_to_request(db, new_request.id, file_categories)

        # Check for any upload warnings or errors
        upload_warnings = []
        upload_errors = []

        for category, result in upload_results.items():
            if isinstance(result, dict):
                if result.get("warnings"):
                    upload_warnings.extend([f"{category}: {w}" for w in result["warnings"]])
                if result.get("errors"):
                    upload_errors.extend([f"{category}: {e}" for e in result["errors"]])

        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.REQUEST_CREATED,
            description=f"Created civil defense request for: {full_name}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        # Refresh the request to load the files relationship
        db.refresh(new_request)

        # Prepare success message with warnings if any
        success_message = "تم إنشاء الطلب بنجاح!"
        if upload_warnings:
            success_message += f" مع {len(upload_warnings)} تحذير في رفع الملفات."

        return templates.TemplateResponse(
            "requests/request_success.html",
            {
                "request": request,
                "current_user": current_user,
                "new_request": new_request,
                "success": success_message,
                "upload_warnings": upload_warnings,
                "upload_errors": upload_errors
            }
        )

    except Exception as e:
        return templates.TemplateResponse(
            "requests/new_request.html",
            {
                "request": request,
                "current_user": current_user,
                "error": str(e)
            },
            status_code=400
        )


@router.get("/requests/{request_id}", response_class=HTMLResponse)
async def view_request(
    request: Request,
    request_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """View request details by ID"""
    # Enhanced logging for mobile debugging
    user_agent = request.headers.get("User-Agent", "")
    client_ip = request.client.host if request.client else "unknown"
    is_mobile = any(mobile_indicator in user_agent.lower() for mobile_indicator in
                   ['mobile', 'android', 'iphone', 'ipad', 'tablet'])

    logger.info(f"Request access attempt - ID: {request_id}, User: {current_user.username if current_user else 'None'}, "
               f"IP: {client_ip}, Mobile: {is_mobile}, UA: {user_agent[:100]}...")

    req = RequestService.get_request_by_id(db, request_id)

    if not req:
        logger.warning(f"Request {request_id} not found - User: {current_user.username if current_user else 'None'}, "
                      f"Mobile: {is_mobile}, IP: {client_ip}")
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is viewing another user's request
    if req.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_request_viewed",
            description=f"تم عرض الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "is_mobile": is_mobile
            }
        )

    logger.info(f"Request {request_id} accessed successfully - User: {current_user.username}, Mobile: {is_mobile}")
    return templates.TemplateResponse(
        "requests/view_request.html",
        {
            "request": request,
            "current_user": current_user,
            "req": req
        }
    )


@router.get("/requests/{request_id}/view", response_class=HTMLResponse)
async def view_request_with_view_suffix(
    request: Request,
    request_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """View request details by ID with /view suffix - same as above but with /view URL pattern"""
    # Enhanced logging for mobile debugging
    user_agent = request.headers.get("User-Agent", "")
    client_ip = request.client.host if request.client else "unknown"
    is_mobile = any(mobile_indicator in user_agent.lower() for mobile_indicator in
                   ['mobile', 'android', 'iphone', 'ipad', 'tablet'])

    logger.info(f"Request access attempt (with /view) - ID: {request_id}, User: {current_user.username if current_user else 'None'}, "
               f"IP: {client_ip}, Mobile: {is_mobile}, UA: {user_agent[:100]}...")

    req = RequestService.get_request_by_id(db, request_id)

    if not req:
        logger.warning(f"Request {request_id} not found - User: {current_user.username if current_user else 'None'}, "
                      f"Mobile: {is_mobile}, IP: {client_ip}")
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is viewing another user's request
    if req.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_request_viewed",
            description=f"تم عرض الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "is_mobile": is_mobile,
                "view_type": "detailed_view"
            }
        )

    logger.info(f"Request {request_id} accessed successfully (with /view) - User: {current_user.username}, Mobile: {is_mobile}")

    return templates.TemplateResponse(
        "requests/view_request.html",
        {
            "request": request,
            "current_user": current_user,
            "req": req
        }
    )


@router.get("/request/{unique_code}", response_class=HTMLResponse)
async def view_request_by_code(
    request: Request,
    unique_code: str,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """View request details by unique code (secure link)"""
    req = RequestService.get_request_by_unique_code(db, unique_code)

    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is viewing another user's request by unique code
    if req.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_request_viewed",
            description=f"تم عرض الطلب {req.request_number} بواسطة الرمز الفريد بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "unique_code": unique_code,
                "access_method": "unique_code"
            }
        )

    return templates.TemplateResponse(
        "requests/view_request.html",
        {
            "request": request,
            "current_user": current_user,
            "req": req,
            "secure_link": True  # Flag to indicate this was accessed via secure link
        }
    )


@router.get("/requests", response_class=HTMLResponse)
async def list_requests(
    request: Request,
    search: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=10, le=100),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Enhanced user requests page - users see their own requests, admins see all requests"""
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = RequestStatus(status)
        except ValueError:
            pass

    # Parse date filters
    date_from_parsed = None
    date_to_parsed = None
    if date_from:
        try:
            from datetime import datetime
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Calculate pagination
    skip = (page - 1) * per_page

    # Check if user is admin
    is_admin = current_user.role == UserRole.ADMIN

    if is_admin:
        # Admin can see all requests
        requests = RequestService.get_all_requests(
            db,
            skip=skip,
            limit=per_page,
            status=status_filter,
            search_query=search,
            date_from=date_from_parsed,
            date_to=date_to_parsed
        )

        # Get total count for pagination
        total_requests = RequestService.get_all_requests_count(
            db,
            status=status_filter,
            search_query=search,
            date_from=date_from_parsed,
            date_to=date_to_parsed
        )

        # Get system-wide request statistics for admin
        user_stats = RequestService.get_request_statistics(db)
    else:
        # Regular user sees only their own requests
        requests = RequestService.get_user_requests_enhanced(
            db,
            current_user.id,
            skip=skip,
            limit=per_page,
            status=status_filter,
            search_query=search,
            date_from=date_from_parsed,
            date_to=date_to_parsed
        )

        # Get total count for pagination
        total_requests = RequestService.get_user_requests_count(
            db,
            current_user.id,
            status=status_filter,
            search_query=search,
            date_from=date_from_parsed,
            date_to=date_to_parsed
        )

        # Get user's request statistics
        user_stats = RequestService.get_user_request_statistics(db, current_user.id)

    # Calculate pagination info
    total_pages = (total_requests + per_page - 1) // per_page

    return templates.TemplateResponse(
        "requests/list_requests.html",
        {
            "request": request,
            "current_user": current_user,
            "requests": requests,
            "current_search": search,
            "current_status": status,
            "current_page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_requests": total_requests,
            "user_stats": user_stats,
            "statuses": [s.value for s in RequestStatus],
            "is_admin": is_admin
        }
    )


@router.post("/requests/bulk-action")
async def user_bulk_request_action(
    request: Request,
    action: str = Form(...),
    request_ids: List[int] = Form(...),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Perform bulk action on user's own requests only"""
    if not request_ids:
        return templates.TemplateResponse(
            "requests/list_requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": RequestService.get_user_requests_enhanced(db, current_user.id, limit=20),
                "statuses": [s.value for s in RequestStatus],
                "error": "لم يتم اختيار أي طلبات"
            },
            status_code=400
        )

    # Verify all requests belong to current user
    user_request_ids = [r.id for r in RequestService.get_user_requests(db, current_user.id, limit=1000)]
    invalid_ids = [rid for rid in request_ids if rid not in user_request_ids]

    if invalid_ids:
        return templates.TemplateResponse(
            "requests/list_requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": RequestService.get_user_requests_enhanced(db, current_user.id, limit=20),
                "statuses": [s.value for s in RequestStatus],
                "error": "غير مسموح بالوصول لبعض الطلبات المحددة"
            },
            status_code=403
        )

    success_count = 0
    total_count = len(request_ids)

    try:
        if action == "delete":
            # Only allow deletion of pending requests
            for request_id in request_ids:
                req = RequestService.get_request_by_id(db, request_id)
                if req and req.user_id == current_user.id and req.status == RequestStatus.PENDING:
                    if RequestService.delete_request(db, request_id):
                        success_count += 1

        elif action == "mark_completed":
            # Allow users to mark their own requests as completed
            for request_id in request_ids:
                req = RequestService.get_request_by_id(db, request_id)
                if req and req.user_id == current_user.id and req.status in [RequestStatus.PENDING, RequestStatus.IN_PROGRESS]:
                    if RequestService.update_request_status(db, request_id, RequestStatus.COMPLETED, current_user.id):
                        success_count += 1

        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.REQUEST_UPDATED,
            description=f"Bulk action '{action}' performed on {success_count} requests",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        # Redirect back to requests page with success message
        requests = RequestService.get_user_requests_enhanced(db, current_user.id, limit=20)
        user_stats = RequestService.get_user_request_statistics(db, current_user.id)

        return templates.TemplateResponse(
            "requests/list_requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": requests,
                "user_stats": user_stats,
                "statuses": [s.value for s in RequestStatus],
                "success": f"تم تنفيذ العملية على {success_count} من أصل {total_count} طلب"
            }
        )

    except Exception as e:
        requests = RequestService.get_user_requests_enhanced(db, current_user.id, limit=20)
        return templates.TemplateResponse(
            "requests/list_requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": requests,
                "statuses": [s.value for s in RequestStatus],
                "error": f"حدث خطأ أثناء تنفيذ العملية: {str(e)}"
            },
            status_code=500
        )


@router.delete("/requests/{request_id}")
async def delete_request_user(
    request_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Delete request - User can only delete their own requests"""
    # Get the request to verify it exists and check ownership
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check permissions - only admin or request owner can delete
    if current_user.role != UserRole.ADMIN and req.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this request")

    # Log the deletion attempt
    logger.info(f"User {current_user.username} attempting to delete request {request_id}")

    # Delete the request
    success = RequestService.delete_request(db, request_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete request")

    # Log successful deletion
    logger.info(f"User {current_user.username} successfully deleted request {request_id}")

    return {"success": True, "message": "Request deleted successfully"}


@router.post("/requests/{request_id}/delete")
async def delete_request_user_post(
    request_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Delete request via POST - User can only delete their own requests"""
    # Get the request to verify it exists and check ownership
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check permissions - only admin or request owner can delete
    if current_user.role != UserRole.ADMIN and req.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this request")

    # Log the deletion attempt
    logger.info(f"User {current_user.username} attempting to delete request {request_id}")

    # Delete the request
    success = RequestService.delete_request(db, request_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete request")

    # Log successful deletion
    logger.info(f"User {current_user.username} successfully deleted request {request_id}")

    return RedirectResponse(url="/requests?message=Request deleted successfully", status_code=303)


@router.post("/requests/{request_id}/update-status")
async def user_update_request_status(
    request: Request,
    request_id: int,
    status: str = Form(...),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Update status of user's own request"""
    # Get the request and verify ownership - Admin can update any request
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is updating another user's request status
    is_cross_user_access = req.user_id != current_user.id
    if is_cross_user_access:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_request_status_updated",
            description=f"تم تحديث حالة الطلب {req.request_number} إلى {status} بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "old_status": req.status.value if req.status else None,
                "new_status": status,
                "notes": notes
            }
        )

    try:
        new_status = RequestStatus(status)
    except ValueError:
        requests = RequestService.get_user_requests_enhanced(db, current_user.id, limit=20)
        return templates.TemplateResponse(
            "requests/list_requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": requests,
                "statuses": [s.value for s in RequestStatus],
                "error": "حالة غير صحيحة"
            },
            status_code=400
        )

    # Allow users to update to any status (removed restrictions)
    # Users can now change request status to any valid status

    # Update the request status
    updated_req = RequestService.update_request_status(db, request_id, new_status, current_user.id)
    if not updated_req:
        requests = RequestService.get_user_requests_enhanced(db, current_user.id, limit=20)
        return templates.TemplateResponse(
            "requests/list_requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": requests,
                "statuses": [s.value for s in RequestStatus],
                "error": "فشل في تحديث حالة الطلب"
            },
            status_code=500
        )

    # Log activity
    UserService.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=ActivityType.REQUEST_UPDATED,
        description=f"Updated request {req.request_number} status to {new_status.value}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    # Redirect back with success message
    requests = RequestService.get_user_requests_enhanced(db, current_user.id, limit=20)
    user_stats = RequestService.get_user_request_statistics(db, current_user.id)

    return templates.TemplateResponse(
        "requests/list_requests.html",
        {
            "request": request,
            "current_user": current_user,
            "requests": requests,
            "user_stats": user_stats,
            "statuses": [s.value for s in RequestStatus],
            "success": f"تم تحديث حالة الطلب {req.request_number} بنجاح"
        }
    )


@router.get("/api/requests/load-more", response_class=HTMLResponse)
async def load_more_requests(
    request: Request,
    skip: int = 10,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """HTMX endpoint to load more requests for dashboard"""
    # Load next batch of requests
    additional_requests = RequestService.get_user_requests(
        db, current_user.id, skip=skip, limit=10
    )

    return templates.TemplateResponse(
        "dashboard/partials/request_rows.html",
        {
            "request": request,
            "current_user": current_user,
            "requests": additional_requests,
            "next_skip": skip + 10
        }
    )


@router.get("/requests/export")
async def export_user_requests(
    request: Request,
    format: str = Query("csv", regex="^(csv|json)$"),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Export user's own requests to CSV or JSON"""
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = RequestStatus(status)
        except ValueError:
            pass

    # Get all user's requests (no pagination for export)
    requests = RequestService.get_user_requests_enhanced(
        db,
        current_user.id,
        skip=0,
        limit=1000,  # Large limit for export
        status=status_filter,
        search_query=search
    )

    # Log export activity
    UserService.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=ActivityType.DATA_EXPORTED,
        description=f"Exported {len(requests)} requests to {format.upper()}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    if format == "csv":
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        headers = [
            "رقم الطلب", "الكود الفريد", "الاسم الكامل", "الرقم الشخصي",
            "رقم الهاتف", "رقم المبنى", "اسم الطريق", "المجمع",
            "رقم ملف الدفاع المدني", "رقم رخصة البناء", "الحالة",
            "تاريخ الإنشاء", "تاريخ التحديث"
        ]
        writer.writerow(headers)

        # Write data
        for req in requests:
            writer.writerow([
                req.request_number or "",
                req.unique_code or "",
                req.full_name or "",
                req.personal_number or "",
                req.phone_number or "",
                req.building_name or "",
                req.road_name or "",
                req.building_number or "",
                req.civil_defense_file_number or "",
                req.building_permit_number or "",
                req.status.value if req.status else "",
                req.created_at.strftime('%Y-%m-%d %H:%M:%S') if req.created_at else "",
                req.updated_at.strftime('%Y-%m-%d %H:%M:%S') if req.updated_at else ""
            ])

        # Create response
        output.seek(0)
        filename = f"my_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),  # UTF-8 BOM for Excel
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    elif format == "json":
        # Create JSON content
        json_data = []
        for req in requests:
            json_data.append({
                "request_number": req.request_number,
                "unique_code": req.unique_code,
                "full_name": req.full_name,
                "personal_number": req.personal_number,
                "phone_number": req.phone_number,
                "building_name": req.building_name,
                "road_name": req.road_name,
                "building_number": req.building_number,
                "civil_defense_file_number": req.civil_defense_file_number,
                "building_permit_number": req.building_permit_number,
                "status": req.status.value if req.status else None,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "updated_at": req.updated_at.isoformat() if req.updated_at else None,
                "licenses_section": req.licenses_section,
                "fire_equipment_section": req.fire_equipment_section,
                "commercial_records_section": req.commercial_records_section,
                "engineering_offices_section": req.engineering_offices_section,
                "hazardous_materials_section": req.hazardous_materials_section
            })

        import json
        json_content = json.dumps(json_data, ensure_ascii=False, indent=2)
        filename = f"my_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return StreamingResponse(
            io.BytesIO(json_content.encode('utf-8')),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.get("/requests/{request_id}/edit", response_class=HTMLResponse)
async def edit_request_form(
    request: Request,
    request_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Display request edit form"""
    req = RequestService.get_request_by_id(db, request_id)

    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is editing another user's request
    if req.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_request_viewed",
            description=f"تم الوصول إلى صفحة تعديل الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "action": "edit_form_accessed"
            }
        )

    # Allow all users to edit their own requests regardless of status
    # (Removed status restriction - users can now edit requests in any status)

    return templates.TemplateResponse(
        "requests/edit_request.html",
        {
            "request": request,
            "current_user": current_user,
            "req": req,
            "statuses": [s.value for s in RequestStatus]  # Show statuses to all users
        }
    )


@router.post("/requests/{request_id}/edit")
async def update_request(
    request: Request,
    request_id: int,
    # Civil Defense fields
    full_name: str = Form(...),
    personal_number: str = Form(...),
    phone_number: Optional[str] = Form(None),
    building_name: Optional[str] = Form(None),
    road_name: Optional[str] = Form(None),
    building_number: Optional[str] = Form(None),
    civil_defense_file_number: Optional[str] = Form(None),
    building_permit_number: Optional[str] = Form(None),
    # Service sections (as strings to handle "true"/"false" from form)
    licenses_section: str = Form("false"),
    fire_equipment_section: str = Form("false"),
    commercial_records_section: str = Form("false"),
    engineering_offices_section: str = Form("false"),
    hazardous_materials_section: str = Form("false"),
    # Legacy fields
    request_name: Optional[str] = Form(None),
    request_title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    # File uploads
    architectural_plans: List[UploadFile] = FastAPIFile(None),
    electrical_mechanical_plans: List[UploadFile] = FastAPIFile(None),
    inspection_department: List[UploadFile] = FastAPIFile(None),
    fire_equipment_files: List[UploadFile] = FastAPIFile(None),
    commercial_records_files: List[UploadFile] = FastAPIFile(None),
    engineering_offices_files: List[UploadFile] = FastAPIFile(None),
    hazardous_materials_files: List[UploadFile] = FastAPIFile(None),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Update request"""
    req = RequestService.get_request_by_id(db, request_id)

    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is editing another user's request
    is_cross_user_edit = req.user_id != current_user.id
    if is_cross_user_edit:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_request_edited",
            description=f"تم تعديل الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "action": "request_edited"
            }
        )

    # Allow all users to edit their own requests regardless of status
    # (Removed status restriction - users can now edit requests in any status)

    try:
        # Convert string boolean values to actual booleans
        def str_to_bool(value: str) -> bool:
            return value.lower() in ('true', '1', 'yes', 'on')

        licenses_section_bool = str_to_bool(licenses_section)
        fire_equipment_section_bool = str_to_bool(fire_equipment_section)
        commercial_records_section_bool = str_to_bool(commercial_records_section)
        engineering_offices_section_bool = str_to_bool(engineering_offices_section)
        hazardous_materials_section_bool = str_to_bool(hazardous_materials_section)

        # Validate personal number
        if personal_number and len(personal_number) != 9:
            return templates.TemplateResponse(
                "requests/edit_request.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "req": req,
                    "statuses": [s.value for s in RequestStatus],
                    "error": "الرقم الشخصي يجب أن يكون 9 أرقام بالضبط"
                },
                status_code=400
            )

        # Validate status if provided (admin only)
        new_status = None
        if status and current_user.role == UserRole.ADMIN:
            try:
                new_status = RequestStatus(status)
            except ValueError:
                return templates.TemplateResponse(
                    "requests/edit_request.html",
                    {
                        "request": request,
                        "current_user": current_user,
                        "req": req,
                        "statuses": [s.value for s in RequestStatus],
                        "error": "حالة الطلب غير صحيحة"
                    },
                    status_code=400
                )

        # Update request with civil defense fields
        updated_request = RequestService.update_civil_defense_request(
            db=db,
            request_id=request_id,
            # Civil Defense fields
            full_name=full_name,
            personal_number=personal_number,
            phone_number=phone_number,
            building_name=building_name,
            road_name=road_name,
            building_number=building_number,
            civil_defense_file_number=civil_defense_file_number,
            building_permit_number=building_permit_number,
            # Service sections (using converted boolean values)
            licenses_section=licenses_section_bool,
            fire_equipment_section=fire_equipment_section_bool,
            commercial_records_section=commercial_records_section_bool,
            engineering_offices_section=engineering_offices_section_bool,
            hazardous_materials_section=hazardous_materials_section_bool,
            # Legacy fields
            request_name=request_name,
            request_title=request_title,
            description=description,
            status=new_status
        )

        if not updated_request:
            return templates.TemplateResponse(
                "errors/404.html",
                {"request": request, "current_user": current_user},
                status_code=404
            )

        # Handle file uploads with enhanced error handling
        uploaded_files_count = 0
        file_upload_errors = []
        file_categories = [
            (architectural_plans, "architectural_plans"),
            (electrical_mechanical_plans, "electrical_mechanical_plans"),
            (inspection_department, "inspection_department"),
            (fire_equipment_files, "fire_equipment_files"),
            (commercial_records_files, "commercial_records_files"),
            (engineering_offices_files, "engineering_offices_files"),
            (hazardous_materials_files, "hazardous_materials_files")
        ]

        for files, category in file_categories:
            if files and any(f.filename for f in files):
                valid_files = [f for f in files if f.filename and f.filename.strip()]
                if valid_files:
                    try:
                        logger.info(f"Processing {len(valid_files)} files for category {category}")
                        file_result = await RequestService.add_files_to_request(
                            db=db, request_id=updated_request.id, files=valid_files, category=category
                        )
                        saved_count = len(file_result.get("saved_files", []))
                        uploaded_files_count += saved_count
                        logger.info(f"Successfully uploaded {saved_count} files for category {category}")

                        # Add any warnings to errors list
                        if file_result.get("warnings"):
                            file_upload_errors.extend(file_result["warnings"])

                    except Exception as file_error:
                        error_msg = f"فشل رفع الملفات في فئة {category}: {str(file_error)}"
                        file_upload_errors.append(error_msg)
                        logger.error(f"File upload failed for category {category}: {str(file_error)}")

        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.REQUEST_UPDATED,
            description=f"Request {updated_request.request_number} updated with {uploaded_files_count} new files",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        success_message = "تم تحديث الطلب بنجاح"
        if uploaded_files_count > 0:
            success_message += f" مع إضافة {uploaded_files_count} ملف جديد"

        # Refresh the request to get updated file list
        db.refresh(updated_request)

        # Prepare template context
        template_context = {
            "request": request,
            "current_user": current_user,
            "req": updated_request,
            "statuses": [s.value for s in RequestStatus],
            "success": success_message
        }

        # Add file upload errors if any
        if file_upload_errors:
            template_context["file_upload_warnings"] = file_upload_errors

        return templates.TemplateResponse(
            "requests/edit_request.html",
            template_context
        )

    except Exception as e:
        return templates.TemplateResponse(
            "requests/edit_request.html",
            {
                "request": request,
                "current_user": current_user,
                "req": req,
                "statuses": [s.value for s in RequestStatus],
                "error": f"حدث خطأ أثناء تحديث الطلب: {str(e)}"
            },
            status_code=500
        )


@router.delete("/requests/{request_id}/files/{file_id}")
async def delete_request_file(
    request: Request,
    request_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Delete a file from request"""
    try:
        # Get the request
        req = RequestService.get_request_by_id(db, request_id)
        if not req:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Request not found"}
            )

        # Log cross-user access if user is deleting files from another user's request
        if req.user_id != current_user.id:
            from app.utils.request_utils import log_cross_user_activity
            log_cross_user_activity(
                db=db,
                request_owner_id=req.user_id,
                accessing_user_id=current_user.id,
                accessing_user_name=current_user.full_name or current_user.username,
                activity_type="cross_user_file_deleted",
                description=f"تم حذف ملف من الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username}",
                request=request,
                details={
                    "request_id": req.id,
                    "request_number": req.request_number,
                    "file_id": file_id,
                    "action": "file_deleted"
                }
            )

        # Get the file
        from app.models.file import File
        file = db.query(File).filter(
            File.id == file_id,
            File.request_id == request_id
        ).first()

        if not file:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "File not found"}
            )

        # Store file info for logging
        file_info = {
            "id": file.id,
            "original_filename": file.original_filename,
            "file_category": file.file_category
        }

        # Delete the file
        success = RequestService.delete_file_from_request(db, file_id)

        if success:
            # Log activity
            from app.services.activity_service import ActivityService
            ActivityService.log_activity(
                db=db,
                user_id=current_user.id,
                activity_type="file_deleted",
                description=f"Deleted file {file_info['original_filename']} from request {req.request_number}",
                details={
                    "file_id": file_info["id"],
                    "filename": file_info["original_filename"],
                    "category": file_info["file_category"],
                    "request_id": req.id,
                    "request_number": req.request_number
                }
            )

            return JSONResponse(
                status_code=200,
                content={"success": True, "message": "File deleted successfully"}
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to delete file"}
            )

    except Exception as e:
        logger.error(f"Error deleting file {file_id} from request {request_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/requests/{request_id}/files", response_class=HTMLResponse)
async def manage_request_files(
    request: Request,
    request_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Manage request files"""
    req = RequestService.get_request_by_id(db, request_id)

    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is accessing files from another user's request
    if req.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_file_accessed",
            description=f"تم الوصول إلى ملفات الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "action": "files_page_accessed"
            }
        )

    return templates.TemplateResponse(
        "requests/manage_files.html",
        {
            "request": request,
            "current_user": current_user,
            "req": req
        }
    )


@router.post("/requests/{request_id}/files/add")
async def add_files_to_request(
    request: Request,
    request_id: int,
    files: List[UploadFile] = FastAPIFile(...),
    file_category: str = Form("additional_documents"),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Add files to existing request with category support"""
    req = RequestService.get_request_by_id(db, request_id)

    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is downloading files from another user's request
    if req.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_file_accessed",
            description=f"تم تحميل ملف من الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "action": "file_download"
            }
        )

    try:
        # Add files with enhanced error handling and category support
        if files and files[0].filename:  # Check if files were actually uploaded
            # Validate category
            valid_categories = [
                "additional_documents", "architectural_plans", "electrical_mechanical_plans",
                "inspection_department", "fire_equipment_files", "commercial_records_files",
                "engineering_offices_files", "hazardous_materials_files"
            ]

            if file_category not in valid_categories:
                file_category = "additional_documents"  # Default fallback

            upload_result = await RequestService.add_files_to_request(db, request_id, files, file_category)

            # Extract results
            saved_files = upload_result.get("saved_files", [])
            warnings = upload_result.get("warnings", [])
            errors = upload_result.get("errors", [])
            successful_uploads = upload_result.get("successful_uploads", len(saved_files))

            # Log activity
            UserService.log_activity(
                db=db,
                user_id=current_user.id,
                activity_type=ActivityType.REQUEST_UPDATED,
                description=f"Added {successful_uploads} files to request {req.request_number} in category '{file_category}'",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )

            # Refresh request data
            req = RequestService.get_request_by_id(db, request_id)

            # Prepare success message with category info
            category_names = {
                "additional_documents": "مستندات إضافية",
                "architectural_plans": "المخططات المعمارية",
                "electrical_mechanical_plans": "المخططات الكهربائية والميكانيكية",
                "inspection_department": "قسم التفتيش",
                "fire_equipment_files": "ملفات معدات مقاومة الحريق",
                "commercial_records_files": "ملفات السجلات التجارية",
                "engineering_offices_files": "ملفات المكاتب الهندسية",
                "hazardous_materials_files": "ملفات المواد الخطرة"
            }

            category_display = category_names.get(file_category, file_category)
            success_message = f"تم إضافة {successful_uploads} ملف بنجاح في فئة '{category_display}'"
            if warnings:
                success_message += f" مع {len(warnings)} تحذير"

            return templates.TemplateResponse(
                "requests/manage_files.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "req": req,
                    "success": success_message,
                    "upload_warnings": warnings,
                    "upload_errors": errors
                }
            )
        else:
            return templates.TemplateResponse(
                "requests/manage_files.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "req": req,
                    "error": "لم يتم اختيار أي ملفات"
                }
            )

    except Exception as e:
        return templates.TemplateResponse(
            "requests/manage_files.html",
            {
                "request": request,
                "current_user": current_user,
                "req": req,
                "error": f"حدث خطأ أثناء إضافة الملفات: {str(e)}"
            }
        )


@router.post("/requests/{request_id}/files/{file_id}/delete")
async def delete_file_from_request(
    request: Request,
    request_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Delete file from request"""
    req = RequestService.get_request_by_id(db, request_id)

    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Log cross-user access if user is downloading files from another user's request
    if req.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=req.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_file_accessed",
            description=f"تم تحميل جميع ملفات الطلب {req.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=request,
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "action": "all_files_download"
            }
        )

    # Delete file
    success = RequestService.delete_file_from_request(db, file_id)

    if success:
        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.REQUEST_UPDATED,
            description=f"Deleted file from request {req.request_number}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        # Refresh request data
        req = RequestService.get_request_by_id(db, request_id)

        return templates.TemplateResponse(
            "requests/manage_files.html",
            {
                "request": request,
                "current_user": current_user,
                "req": req,
                "success": "تم حذف الملف بنجاح"
            }
        )
    else:
        return templates.TemplateResponse(
            "requests/manage_files.html",
            {
                "request": request,
                "current_user": current_user,
                "req": req,
                "error": "فشل في حذف الملف"
            }
        )


@router.get("/profile", response_class=HTMLResponse)
async def user_profile(
    request: Request,
    current_user: User = Depends(get_current_user_cookie)
):
    """User profile page"""
    # Get user avatar URL
    from app.services.avatar_service import AvatarService
    from app.database import get_db
    db = next(get_db())
    profile_user_avatar_url = AvatarService.get_avatar_url(current_user.id, current_user.full_name, db)
    db.close()

    return templates.TemplateResponse(
        "profile/profile.html",
        {
            "request": request,
            "current_user": current_user,
            "profile_user": current_user,  # Same user for own profile
            "profile_user_avatar_url": profile_user_avatar_url
        }
    )


@router.get("/profile/{user_id}", response_class=HTMLResponse)
async def view_user_profile(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """View specific user profile (for admins)"""
    # Check if current user is admin or viewing own profile
    if current_user.role.value not in ['admin', 'manager'] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="غير مسموح لك بعرض هذا الملف الشخصي")

    # Get the target user
    profile_user = UserService.get_user_by_id(db, user_id)
    if not profile_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    # Get profile user avatar URL
    from app.services.avatar_service import AvatarService
    profile_user_avatar_url = AvatarService.get_avatar_url(profile_user.id, profile_user.full_name, db)

    return templates.TemplateResponse(
        "profile/profile.html",
        {
            "request": request,
            "current_user": current_user,
            "profile_user": profile_user,  # Different user for admin viewing
            "profile_user_avatar_url": profile_user_avatar_url
        }
    )


@router.post("/profile/update")
async def update_profile(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    username: str = Form(None),
    password: str = Form(None),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    try:
        # Update user profile
        updated_user = UserService.update_user(
            db=db,
            user_id=current_user.id,
            full_name=full_name,
            email=email
        )

        # Update password if provided
        if password and password.strip():
            from app.utils.auth import get_password_hash
            updated_user.hashed_password = get_password_hash(password)
            db.commit()
            db.refresh(updated_user)

        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.PROFILE_UPDATED,
            description="Profile updated",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        # Get user avatar URL for the response
        from app.services.avatar_service import AvatarService
        profile_user_avatar_url = AvatarService.get_avatar_url(updated_user.id, updated_user.full_name, db)

        return RedirectResponse(url="/profile?profile_updated=true", status_code=303)

    except Exception as e:
        # Get user avatar URL for error response
        from app.services.avatar_service import AvatarService
        profile_user_avatar_url = AvatarService.get_avatar_url(current_user.id, current_user.full_name, db)

        return templates.TemplateResponse(
            "profile/profile.html",
            {
                "request": request,
                "current_user": current_user,
                "profile_user": current_user,
                "profile_user_avatar_url": profile_user_avatar_url,
                "error": str(e)
            },
            status_code=400
        )


@router.get("/migrate-civil-defense")
async def migrate_civil_defense_database(
    request: Request,
    current_user: User = Depends(get_current_user_cookie)
):
    """Migrate database to add civil defense fields - Admin only"""
    # Only allow admin users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied - Admin only")

    migration_commands = [
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS full_name VARCHAR(200);",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS personal_number VARCHAR(9);",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS phone_number VARCHAR(15);",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS building_name VARCHAR(200);",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS road_name VARCHAR(200);",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS building_number VARCHAR(100);",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS civil_defense_file_number VARCHAR(100);",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS building_permit_number VARCHAR(100);",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS licenses_section BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS fire_equipment_section BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS commercial_records_section BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS engineering_offices_section BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE requests ADD COLUMN IF NOT EXISTS hazardous_materials_section BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE files ADD COLUMN IF NOT EXISTS file_category VARCHAR(100) DEFAULT 'general';",
        "UPDATE requests SET licenses_section = FALSE WHERE licenses_section IS NULL;",
        "UPDATE requests SET fire_equipment_section = FALSE WHERE fire_equipment_section IS NULL;",
        "UPDATE requests SET commercial_records_section = FALSE WHERE commercial_records_section IS NULL;",
        "UPDATE requests SET engineering_offices_section = FALSE WHERE engineering_offices_section IS NULL;",
        "UPDATE requests SET hazardous_materials_section = FALSE WHERE hazardous_materials_section IS NULL;",
        "UPDATE files SET file_category = 'general' WHERE file_category IS NULL;",
        "ALTER TABLE requests ALTER COLUMN licenses_section SET NOT NULL;",
        "ALTER TABLE requests ALTER COLUMN fire_equipment_section SET NOT NULL;",
        "ALTER TABLE requests ALTER COLUMN commercial_records_section SET NOT NULL;",
        "ALTER TABLE requests ALTER COLUMN engineering_offices_section SET NOT NULL;",
        "ALTER TABLE requests ALTER COLUMN hazardous_materials_section SET NOT NULL;",
        "ALTER TABLE files ALTER COLUMN file_category SET NOT NULL;"
    ]

    results = []
    success_count = 0

    try:
        with engine.connect() as connection:
            for i, command in enumerate(migration_commands, 1):
                try:
                    connection.execute(text(command))
                    connection.commit()
                    results.append(f"✅ [{i:2d}/{len(migration_commands)}] Success: {command[:50]}...")
                    success_count += 1
                except Exception as e:
                    results.append(f"⚠️  [{i:2d}/{len(migration_commands)}] Warning: {str(e)[:50]}...")
                    connection.rollback()

        # Log the migration activity
        UserService.log_activity(
            db=next(get_db()),
            user_id=current_user.id,
            activity_type=ActivityType.SYSTEM_UPDATE,
            description="Civil defense database migration completed",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        return {
            "success": True,
            "message": f"Migration completed! {success_count}/{len(migration_commands)} commands executed successfully.",
            "results": results
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Migration failed: {str(e)}",
            "results": results
        }


@router.get("/fix-legacy-fields")
async def fix_legacy_fields_nullable(
    request: Request,
    current_user: User = Depends(get_current_user_cookie)
):
    """Fix legacy fields to be nullable for civil defense forms - Admin only"""
    # Only allow admin users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied - Admin only")

    fix_commands = [
        "ALTER TABLE requests ALTER COLUMN request_name DROP NOT NULL;",
        "ALTER TABLE requests ALTER COLUMN request_title DROP NOT NULL;",
        "ALTER TABLE requests ALTER COLUMN description DROP NOT NULL;"
    ]

    results = []
    success_count = 0

    try:
        with engine.connect() as connection:
            for i, command in enumerate(fix_commands, 1):
                try:
                    connection.execute(text(command))
                    connection.commit()
                    results.append(f"✅ [{i:2d}/{len(fix_commands)}] Success: {command}")
                    success_count += 1
                except Exception as e:
                    results.append(f"⚠️  [{i:2d}/{len(fix_commands)}] Warning: {str(e)}")
                    connection.rollback()

        # Log the fix activity
        UserService.log_activity(
            db=next(get_db()),
            user_id=current_user.id,
            activity_type=ActivityType.SYSTEM_UPDATE,
            description="Fixed legacy fields to be nullable",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        return {
            "success": True,
            "message": f"Legacy fields fix completed! {success_count}/{len(fix_commands)} commands executed successfully.",
            "results": results
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Fix failed: {str(e)}",
            "results": results
        }


@router.get("/debug/file-upload-test", response_class=HTMLResponse)
async def file_upload_test(request: Request):
    """Debug page to test file upload styling"""
    return templates.TemplateResponse("debug/file_upload_test.html", {"request": request})


# ===== FILE DOWNLOAD ROUTES =====

@router.get("/files/download/{file_id}")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Download file by ID with permission check"""
    # Get file from database
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Log cross-user access if user is downloading file from another user's request
    if file.request.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=file.request.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_file_accessed",
            description=f"تم تحميل الملف {file.original_filename} من الطلب {file.request.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=None,  # No request object available here
            details={
                "request_id": file.request.id,
                "request_number": file.request.request_number,
                "file_id": file.id,
                "filename": file.original_filename,
                "action": "direct_file_download"
            }
        )

    # Check if file exists on disk
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Return file for download
    return FileResponse(
        path=file.file_path,
        filename=file.original_filename,
        media_type=file.mime_type
    )


@router.get("/files/view/{file_id}")
async def view_file(
    file_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """View file in browser by ID with permission check"""
    # Get file from database
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Log cross-user access if user is viewing file from another user's request
    if file.request.user_id != current_user.id:
        from app.utils.request_utils import log_cross_user_activity
        log_cross_user_activity(
            db=db,
            request_owner_id=file.request.user_id,
            accessing_user_id=current_user.id,
            accessing_user_name=current_user.full_name or current_user.username,
            activity_type="cross_user_file_accessed",
            description=f"تم عرض الملف {file.original_filename} من الطلب {file.request.request_number} بواسطة {current_user.full_name or current_user.username}",
            request=None,  # No request object available here
            details={
                "request_id": file.request.id,
                "request_number": file.request.request_number,
                "file_id": file.id,
                "filename": file.original_filename,
                "action": "direct_file_view"
            }
        )

    # Check if file exists on disk
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Return file for viewing in browser
    return FileResponse(
        path=file.file_path,
        filename=file.original_filename,
        media_type=file.mime_type,
        headers={"Content-Disposition": "inline"}
    )


@router.get("/test-file-upload", response_class=HTMLResponse)
async def test_file_upload(
    request: Request,
    current_user: User = Depends(get_current_user_cookie)
):
    """Test page for file upload functionality"""
    return templates.TemplateResponse(
        "debug/file_upload_test.html",
        {
            "request": request,
            "current_user": current_user
        }
    )


@router.get("/my-profile", response_class=HTMLResponse)
async def my_profile_table(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """User's personal profile table view - shows only their own data"""

    # Get user avatar URL
    user_avatar_url = AvatarService.get_avatar_url(current_user.id, current_user.full_name, db)

    # Get user requests
    user_requests = RequestService.get_requests_by_user_id(db, current_user.id, limit=1000)

    # Calculate user statistics
    user_stats = {
        "total_requests": len(user_requests),
        "pending_requests": len([r for r in user_requests if r.status == RequestStatus.PENDING]),
        "completed_requests": len([r for r in user_requests if r.status == RequestStatus.COMPLETED]),
        "in_progress_requests": len([r for r in user_requests if r.status == RequestStatus.IN_PROGRESS]),
        "rejected_requests": len([r for r in user_requests if r.status == RequestStatus.REJECTED])
    }

    # Get recent activities
    recent_activities = ActivityService.get_user_activities(
        db=db,
        user_id=current_user.id,
        limit=10
    )

    # Calculate activity level
    activity_level = "منخفض"
    if len(recent_activities) > 20:
        activity_level = "عالي"
    elif len(recent_activities) > 10:
        activity_level = "متوسط"

    activity_stats = {
        "total_activities": len(recent_activities),
        "activity_level": activity_level,
        "activity_color": "text-green-600" if activity_level == "عالي" else "text-yellow-600" if activity_level == "متوسط" else "text-red-600"
    }

    return templates.TemplateResponse(
        "user/my_profile_table.html",
        {
            "request": request,
            "current_user": current_user,
            "user_avatar_url": user_avatar_url,
            "user_requests": user_requests,
            "user_stats": user_stats,
            "recent_activities": recent_activities,
            "activity_stats": activity_stats
        }
    )


@router.get("/users/table/user-view", response_class=HTMLResponse)
async def users_table_user_view(
    request: Request,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """User view of the users table - shows only their own row"""

    # Get user avatar URL
    user_avatar_url = AvatarService.get_avatar_url(current_user.id, current_user.full_name, db)

    # Get user requests
    user_requests = RequestService.get_requests_by_user_id(db, current_user.id, limit=1000)

    # Calculate user statistics
    user_stats = {
        "total_requests": len(user_requests),
        "pending_requests": len([r for r in user_requests if r.status == RequestStatus.PENDING]),
        "completed_requests": len([r for r in user_requests if r.status == RequestStatus.COMPLETED]),
        "in_progress_requests": len([r for r in user_requests if r.status == RequestStatus.IN_PROGRESS]),
        "rejected_requests": len([r for r in user_requests if r.status == RequestStatus.REJECTED])
    }

    # Get recent activities
    recent_activities = ActivityService.get_user_activities(
        db=db,
        user_id=current_user.id,
        limit=10
    )

    # Create a single-user list for the template
    users_list = [current_user]

    # Add avatar URL to user object for template
    current_user.avatar_url = user_avatar_url
    current_user.requests = user_requests

    return templates.TemplateResponse(
        "user/users_table_user_view.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users_list,
            "user_stats": user_stats,
            "recent_activities": recent_activities,
            "total_users": 1,
            "active_users": 1 if current_user.is_active else 0,
            "total_requests": user_stats["total_requests"],
            "pending_requests": user_stats["pending_requests"]
        }
    )
