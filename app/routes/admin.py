from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File as FastAPIFile, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse, Response

from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from datetime import datetime as dt, timezone, timedelta
from app.database import get_db
from app.utils.auth import verify_token
from app.services.user_service import UserService
from app.services.request_service import RequestService
from app.services.achievement_service import AchievementService
from app.services.avatar_service import AvatarService
from app.services.activity_service import ActivityService
from app.models.user import User, UserRole, UserStatus
from app.models.request import RequestStatus

logger = logging.getLogger(__name__)
from app.models.activity import Activity, ActivityType
from app.utils.file_handler import FileHandler
import pandas as pd
import io
# datetime already imported as dt above
import csv

# PDF generation imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

router = APIRouter(prefix="/admin")
from app.utils.templates import templates


async def require_admin_cookie(request: Request, db: Session = Depends(get_db)) -> User:
    """Require admin role using cookie authentication"""
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

    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return user


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


async def require_user_access_or_admin(request: Request, user_id: int, db: Session = Depends(get_db)) -> User:
    """Require user to be either the target user or an admin"""
    current_user = await get_current_user_cookie(request, db)

    # Allow access if user is admin
    if current_user.role == UserRole.ADMIN:
        return current_user

    # Allow access if user is accessing their own data
    if current_user.id == user_id:
        return current_user

    # Deny access otherwise
    raise HTTPException(
        status_code=403,
        detail="Access denied. You can only access your own data or need admin privileges."
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Admin dashboard"""
    # Get system statistics
    request_stats = RequestService.get_request_statistics(db)

    # Get recent requests
    recent_requests = RequestService.get_all_requests(db, limit=10)

    # Get all users count
    all_users = UserService.get_all_users(db, limit=1000)
    user_count = len(all_users)
    admin_count = len([u for u in all_users if u.role == UserRole.ADMIN])
    active_users = len([u for u in all_users if u.is_active])

    # Get user monthly chart data
    user_chart_data = RequestService.get_user_monthly_chart_data(db)

    # Get user progress tracking data
    user_progress_data = RequestService.get_user_progress_tracking(db)



    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "request_stats": request_stats,
            "recent_requests": recent_requests,
            "user_stats": {
                "total": user_count,
                "admins": admin_count,
                "active": active_users
            },
            "user_chart_data": user_chart_data,
            "user_progress_data": user_progress_data
        }
    )


@router.get("/stats", response_class=HTMLResponse)
async def admin_stats_dashboard(
    request: Request,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Admin Stats Dashboard with comprehensive analytics"""
    from app.services.achievement_service import AchievementService

    # Get comprehensive stats data
    stats_data = AchievementService.get_admin_stats_dashboard_data(db)

    # Get users competition data for the bubble chart
    users_competition_data = RequestService.get_users_competition_data(db)

    return templates.TemplateResponse(
        "admin/stats.html",
        {
            "request": request,
            "current_user": current_user,
            "stats_data": stats_data,
            "users_competition_data": users_competition_data
        }
    )


@router.get("/users", response_class=HTMLResponse)
async def manage_users(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    approval_filter: Optional[str] = None,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Manage users page with pagination and filtering"""
    try:
        # Validate page and per_page parameters
        page = max(1, page)
        per_page = min(max(10, per_page), 100)  # Between 10 and 100

        # Calculate offset
        offset = (page - 1) * per_page

        # Get users with pagination and filtering
        users = UserService.get_users_with_pagination(
            db=db,
            limit=per_page,
            skip=offset,
            search=search,
            role_filter=role_filter,
            status_filter=status_filter,
            approval_filter=approval_filter
        )

        # Get total count for pagination
        total_users = UserService.get_users_count(
            db=db,
            search=search,
            role_filter=role_filter,
            status_filter=status_filter,
            approval_filter=approval_filter
        )

        # Calculate pagination info
        total_pages = max(1, (total_users + per_page - 1) // per_page) if total_users > 0 else 1
        has_prev = page > 1
        has_next = page < total_pages

        # Get request statistics for the upload section
        request_stats = RequestService.get_request_statistics(db)

        # Get recent requests for display
        recent_requests = RequestService.get_all_requests(db, limit=10)

        # Get approval statistics
        all_users = UserService.get_all_users(db, limit=1000)
        approval_stats = {
            "pending": len([u for u in all_users if u.approval_status == UserStatus.PENDING]),
            "approved": len([u for u in all_users if u.approval_status == UserStatus.APPROVED]),
            "rejected": len([u for u in all_users if u.approval_status == UserStatus.REJECTED])
        }

        return templates.TemplateResponse(
            "admin/users_with_upload.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "request_stats": request_stats,
                "recent_requests": recent_requests,
                # Pagination data
                "current_page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "total_users": total_users,
                "has_prev": has_prev,
                "has_next": has_next,
                # Filter data
                "current_search": search,
                "current_role_filter": role_filter,
                "current_status_filter": status_filter,
                "current_approval_filter": approval_filter,
                # Approval statistics
                "approval_stats": approval_stats,
                "available_roles": [role.value for role in UserRole]
            }
        )

    except Exception as e:
        logger.error(f"Error in manage_users: {e}")
        # Return error page with empty results
        return templates.TemplateResponse(
            "admin/users_with_upload.html",
            {
                "request": request,
                "current_user": current_user,
                "users": [],
                "request_stats": {"total": 0, "pending": 0, "completed": 0, "in_progress": 0},
                "recent_requests": [],
                "current_page": 1,
                "per_page": per_page,
                "total_pages": 1,
                "total_users": 0,
                "has_prev": False,
                "has_next": False,
                "current_search": search,
                "current_role_filter": role_filter,
                "current_status_filter": status_filter,
                "available_roles": [role.value for role in UserRole],
                "error": "حدث خطأ في تحميل المستخدمين. يرجى المحاولة مرة أخرى."
            }
        )


@router.post("/users/upload-request")
async def upload_request_for_user(
    request: Request,
    user_id: int = Form(...),
    request_name: str = Form(...),
    full_name: str = Form(...),
    unique_code: str = Form(...),
    building_permit_number: str = Form(None),
    company_name: str = Form(None),
    files: List[UploadFile] = FastAPIFile(...),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Upload a new request for a specific user"""
    try:
        # Validate that the target user exists
        target_user = UserService.get_user_by_id(db, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create the request
        new_request = RequestService.create_request(
            db=db,
            user_id=user_id,
            request_name=request_name,
            full_name=full_name,
            unique_code=unique_code,
            building_permit_number=building_permit_number,
            company_name=company_name
        )

        # Handle file uploads
        if files and files[0].filename:  # Check if files were actually uploaded
            try:
                # Use RequestService to add files to the request
                file_result = await RequestService.add_files_to_request(
                    db=db,
                    request_id=new_request.id,
                    files=files,
                    category="general"
                )

                uploaded_files = file_result.get("saved_files", [])

                # Log file upload activity
                if uploaded_files:
                    ActivityService.log_activity(
                        db=db,
                        user_id=user_id,
                        activity_type="file_uploaded",
                        description=f"تم رفع {len(uploaded_files)} ملف للطلب {new_request.request_number}",
                        details={
                            "request_id": new_request.id,
                            "request_number": new_request.request_number,
                            "file_count": len(uploaded_files),
                            "uploaded_by_admin": current_user.id
                        }
                    )

            except Exception as file_error:
                logger.warning(f"File upload failed for request {new_request.id}: {str(file_error)}")
                # Continue without failing the entire request creation

        # Log request creation activity
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            activity_type="request_created",
            description=f"تم إنشاء طلب جديد: {new_request.request_number}",
            details={
                "request_id": new_request.id,
                "request_number": new_request.request_number,
                "company_name": company_name,
                "created_by_admin": current_user.id
            }
        )

        return RedirectResponse(
            url=f"/admin/users?success=تم إنشاء الطلب بنجاح للمستخدم {target_user.full_name}",
            status_code=303
        )

    except Exception as e:
        logger.error(f"Error creating request for user {user_id}: {str(e)}")
        return RedirectResponse(
            url=f"/admin/users?error=حدث خطأ أثناء إنشاء الطلب: {str(e)}",
            status_code=303
        )


@router.get("/users/{user_id}/upload-request", response_class=HTMLResponse)
async def upload_request_page(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Display upload request page for a specific user"""
    # Verify access permissions
    current_user = await require_user_access_or_admin(request, user_id, db)

    # Get the target user
    target_user = UserService.get_user_by_id(db, user_id)
    if not target_user:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user}
        )

    # Get user avatar URL
    target_user_avatar_url = AvatarService.get_avatar_url(target_user.id, target_user.full_name, db)

    # Get user statistics
    user_requests = RequestService.get_requests_by_user_id(db, user_id, limit=1000)
    user_stats = {
        "total_requests": len(user_requests),
        "pending_requests": len([r for r in user_requests if r.status == RequestStatus.PENDING]),
        "completed_requests": len([r for r in user_requests if r.status == RequestStatus.COMPLETED]),
        "in_progress_requests": len([r for r in user_requests if r.status == RequestStatus.IN_PROGRESS])
    }

    return templates.TemplateResponse(
        "admin/upload_request.html",
        {
            "request": request,
            "current_user": current_user,
            "target_user": target_user,
            "target_user_avatar_url": target_user_avatar_url,
            "user_stats": user_stats
        }
    )


@router.post("/users/{user_id}/upload-request")
async def create_request_for_user(
    request: Request,
    user_id: int,
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
    db: Session = Depends(get_db)
):
    """Create a new civil defense request for a specific user"""
    try:
        # Verify access permissions
        current_user = await require_user_access_or_admin(request, user_id, db)

        # Validate that the target user exists
        target_user = UserService.get_user_by_id(db, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate personal number (9 digits exactly)
        if not personal_number or len(personal_number) != 9 or not personal_number.isdigit():
            return templates.TemplateResponse(
                "admin/upload_request.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "target_user": target_user,
                    "target_user_avatar_url": AvatarService.get_avatar_url(target_user.id, target_user.full_name, db),
                    "user_stats": RequestService.get_user_request_stats(db, user_id),
                    "error": "الرقم الشخصي يجب أن يكون 9 أرقام بالضبط"
                },
                status_code=400
            )

        # Validate required files
        required_files = [
            (architectural_plans, "مخططات هندسية معمارية"),
            (electrical_mechanical_plans, "مخططات هندسية كهربائية وميكانيكية"),
            (inspection_department, "قسم التفتيش")
        ]

        for file_list, file_name in required_files:
            if not file_list or not any(f.filename for f in file_list):
                return templates.TemplateResponse(
                    "admin/upload_request.html",
                    {
                        "request": request,
                        "current_user": current_user,
                        "target_user": target_user,
                        "target_user_avatar_url": AvatarService.get_avatar_url(target_user.id, target_user.full_name, db),
                        "user_stats": RequestService.get_user_request_stats(db, user_id),
                        "error": f"يجب رفع ملفات {file_name}"
                    },
                    status_code=400
                )

        # Create the request with all fields
        new_request = RequestService.create_request(
            db=db,
            user_id=user_id,
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
            hazardous_materials_section=hazardous_materials_section
        )

        # Handle file uploads for each category with enhanced validation
        file_categories = [
            ("architectural_plans", architectural_plans, "مخططات هندسية معمارية"),
            ("electrical_mechanical_plans", electrical_mechanical_plans, "مخططات هندسية كهربائية وميكانيكية"),
            ("inspection_department", inspection_department, "قسم التفتيش"),
            ("fire_equipment_files", fire_equipment_files, "معدات الحريق"),
            ("commercial_records_files", commercial_records_files, "السجلات التجارية"),
            ("engineering_offices_files", engineering_offices_files, "المكاتب الهندسية"),
            ("hazardous_materials_files", hazardous_materials_files, "المواد الخطرة")
        ]

        total_uploaded_files = 0
        upload_errors = []

        for category, files, category_name in file_categories:
            if files and any(f.filename for f in files):
                try:
                    # Filter out empty files and validate
                    valid_files = []
                    for f in files:
                        if f.filename and f.filename.strip():
                            # Validate file type
                            if not f.filename.lower().endswith('.pdf'):
                                upload_errors.append(f"ملف {f.filename} في {category_name}: يجب أن يكون ملف PDF")
                                continue

                            # Validate file size (10MB limit)
                            content = await f.read()
                            if len(content) > 10 * 1024 * 1024:  # 10MB
                                upload_errors.append(f"ملف {f.filename} في {category_name}: حجم الملف كبير جداً (أكثر من 10 ميجابايت)")
                                continue

                            # Reset file pointer
                            await f.seek(0)
                            valid_files.append(f)

                    if valid_files:
                        # Use RequestService to add files to the request
                        file_result = await RequestService.add_files_to_request(
                            db=db,
                            request_id=new_request.id,
                            files=valid_files,
                            category=category
                        )

                        uploaded_files = file_result.get("saved_files", [])
                        total_uploaded_files += len(uploaded_files)

                except Exception as file_error:
                    logger.warning(f"File upload failed for category {category}: {str(file_error)}")
                    upload_errors.append(f"خطأ في رفع ملفات {category_name}: {str(file_error)}")

        # Commit the transaction to ensure files are persisted
        db.commit()

        # Check for upload errors
        if upload_errors:
            error_message = "تم إنشاء الطلب ولكن حدثت أخطاء في رفع بعض الملفات:\n" + "\n".join(upload_errors)
            return RedirectResponse(
                url=f"/admin/users/{user_id}/upload-request?error={error_message}",
                status_code=303
            )

        # Log request creation activity
        ActivityService.log_activity(
            db=db,
            user_id=user_id,
            activity_type="request_created",
            description=f"تم إنشاء طلب جديد: {new_request.request_number}",
            details={
                "request_id": new_request.id,
                "request_number": new_request.request_number,
                "full_name": full_name,
                "personal_number": personal_number,
                "building_name": building_name,
                "licenses_section": licenses_section,
                "fire_equipment_section": fire_equipment_section,
                "commercial_records_section": commercial_records_section,
                "engineering_offices_section": engineering_offices_section,
                "hazardous_materials_section": hazardous_materials_section,
                "created_by_admin": current_user.id if current_user.role == UserRole.ADMIN else None
            }
        )

        # Log file upload activity if files were uploaded
        if total_uploaded_files > 0:
            ActivityService.log_activity(
                db=db,
                user_id=user_id,
                activity_type="file_uploaded",
                description=f"تم رفع {total_uploaded_files} ملف للطلب {new_request.request_number}",
                details={
                    "request_id": new_request.id,
                    "request_number": new_request.request_number,
                    "file_count": total_uploaded_files,
                    "uploaded_by_admin": current_user.id if current_user.role == UserRole.ADMIN else None
                }
            )

        # Update user achievements
        try:
            from app.services.achievement_service import AchievementService
            AchievementService.update_user_achievements(db, user_id)
        except Exception as achievement_error:
            logger.warning(f"Achievement update failed for user {user_id}: {str(achievement_error)}")

        return RedirectResponse(
            url=f"/admin/users/{user_id}/upload-request?success=تم إنشاء الطلب بنجاح رقم {new_request.request_number}",
            status_code=303
        )

    except Exception as e:
        logger.error(f"Error creating request for user {user_id}: {str(e)}")
        return RedirectResponse(
            url=f"/admin/users/{user_id}/upload-request?error=حدث خطأ أثناء إنشاء الطلب: {str(e)}",
            status_code=303
        )





@router.get("/users/{user_id}/activities", response_class=HTMLResponse)
async def user_activities(
    request: Request,
    user_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=10, le=50),
    db: Session = Depends(get_db)
):
    """View activity log for a specific user"""
    # Verify access permissions
    current_user = await require_user_access_or_admin(request, user_id, db)

    # Get the target user
    target_user = UserService.get_user_by_id(db, user_id)
    if not target_user:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user}
        )

    logger.info(f"Getting activities for user {user_id} ({target_user.username})")

    # Get user activities (automatically filtered to request activities only)
    activities = ActivityService.get_user_activities(
        db,
        user_id=user_id,
        activity_type=None,  # No filtering needed - service already filters to request activities
        date_from=date_from,
        date_to=date_to,
        limit=100
    )

    # Calculate pagination for requests
    skip = (page - 1) * per_page

    # Get user's latest requests with pagination
    user_requests = RequestService.get_requests_by_user_id(
        db,
        user_id=user_id,
        limit=per_page,
        skip=skip
    )

    # Get total count of user requests for pagination
    total_requests = RequestService.get_user_requests_count(db, user_id)
    total_pages = (total_requests + per_page - 1) // per_page

    # Get activity statistics
    activity_stats = ActivityService.get_user_activity_statistics(db, user_id)

    # Get user avatar URL
    from app.services.avatar_service import AvatarService
    target_user_avatar_url = AvatarService.get_avatar_url(target_user.id, target_user.full_name, db)

    return templates.TemplateResponse(
        "admin/user_activities.html",
        {
            "request": request,
            "current_user": current_user,
            "target_user": target_user,
            "target_user_avatar_url": target_user_avatar_url,
            "activities": activities,
            "user_requests": user_requests,
            "activity_stats": activity_stats,
            "current_date_from": date_from,
            "current_date_to": date_to,
            "now": dt.now(timezone.utc),
            # Pagination data
            "current_page": page,
            "total_pages": total_pages,
            "total_requests": total_requests,
            "per_page": per_page,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None
        }
    )





@router.get("/users/{user_id}/requests", response_class=HTMLResponse)
async def user_requests(
    request: Request,
    user_id: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """View requests for a specific user"""
    try:
        logger.info(f"Accessing user requests page for user_id: {user_id}")

        # Verify access permissions
        current_user = await require_user_access_or_admin(request, user_id, db)
        logger.info(f"Access granted for user: {current_user.username} (role: {current_user.role.value})")

        # Get the target user
        target_user = UserService.get_user_by_id(db, user_id)
        if not target_user:
            logger.warning(f"Target user not found: {user_id}")
            return templates.TemplateResponse(
                "errors/404.html",
                {"request": request, "current_user": current_user}
            )

        logger.info(f"Target user found: {target_user.username}")

        # Parse status filter
        status_filter = None
        if status:
            try:
                status_filter = RequestStatus(status)
                logger.info(f"Status filter applied: {status_filter}")
            except ValueError:
                logger.warning(f"Invalid status filter: {status}")
                pass

        # Get user's requests
        user_requests = RequestService.get_requests_by_user_id(
            db,
            user_id=user_id,
            status=status_filter,
            search_query=search,
            limit=100
        )

        logger.info(f"Found {len(user_requests)} requests for user {user_id}")

        # Get user's request statistics
        user_request_stats = RequestService.get_user_request_statistics(db, user_id)
        logger.info(f"User request statistics: {user_request_stats}")

        # Get user avatar URL
        from app.services.avatar_service import AvatarService
        target_user_avatar_url = AvatarService.get_avatar_url(target_user.id, target_user.full_name, db)

        return templates.TemplateResponse(
            "admin/user_requests.html",
            {
                "request": request,
                "current_user": current_user,
                "target_user": target_user,
                "target_user_avatar_url": target_user_avatar_url,
                "user_requests": user_requests,
                "requests": user_requests,       # Keep both for compatibility
                "request_stats": user_request_stats,
                "current_status": status,
                "current_search": search,
                "statuses": [s.value for s in RequestStatus]
            }
        )

    except Exception as e:
        logger.error(f"Error in user_requests route: {str(e)}")
        return templates.TemplateResponse(
            "errors/500.html",
            {"request": request, "error": str(e)},
            status_code=500
        )


@router.get("/users/{user_id}/requests/debug")
async def debug_user_requests(
    user_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check user requests data"""
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
            "requests": formatted_requests[:5],  # Show first 5 for debugging
            "statistics": user_request_stats,
            "route_info": {
                "route": f"/admin/users/{user_id}/requests",
                "accessing_user": current_user.username,
                "accessing_user_role": current_user.role.value
            }
        })

    except Exception as e:
        logger.error(f"Error in debug_user_requests: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Error: {str(e)}"
        })


@router.get("/users/table", response_class=HTMLResponse)
async def users_table_new(
    request: Request,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """New users table page with enhanced design and real data"""
    users = UserService.get_all_users(db, limit=100)

    # Get avatar URLs and request counts for all users
    from app.services.avatar_service import AvatarService
    from app.models.activity import Activity
    # datetime already imported as dt above
    users_with_data = []
    for user in users:
        avatar_url = AvatarService.get_avatar_url(user.id, user.full_name, db)

        # Get real request statistics for each user
        user_request_stats = RequestService.get_user_request_statistics(db, user.id)

        # Get last real activity from activities table
        last_activity = db.query(Activity).filter(
            Activity.user_id == user.id
        ).order_by(Activity.created_at.desc()).first()

        # Calculate last activity time
        if last_activity:
            last_activity_time = last_activity.created_at

            # Handle timezone-aware datetime properly
            if last_activity_time.tzinfo is not None:
                # Convert to UTC naive datetime for comparison
                from datetime import timezone
                last_activity_time = last_activity_time.astimezone(timezone.utc).replace(tzinfo=None)

            # Use timezone-aware current time
            current_time = dt.now(timezone.utc).replace(tzinfo=None)
            time_diff = current_time - last_activity_time

            # Handle negative time differences (future dates)
            if time_diff.total_seconds() < 0:
                last_activity_display = "الآن"
            elif time_diff.days == 0:
                total_seconds = int(time_diff.total_seconds())
                if total_seconds < 60:  # Less than 1 minute
                    last_activity_display = "الآن"
                elif total_seconds < 3600:  # Less than 1 hour
                    minutes = total_seconds // 60
                    last_activity_display = f"منذ {minutes} دقيقة"
                else:  # Less than 24 hours
                    hours = total_seconds // 3600
                    last_activity_display = f"منذ {hours} ساعة"
            elif time_diff.days == 1:
                last_activity_display = "أمس"
            elif time_diff.days < 7:
                last_activity_display = f"منذ {time_diff.days} أيام"
            elif time_diff.days < 30:
                weeks = time_diff.days // 7
                if weeks == 1:
                    last_activity_display = "منذ أسبوع"
                else:
                    last_activity_display = f"منذ {weeks} أسابيع"
            else:
                months = time_diff.days // 30
                if months == 1:
                    last_activity_display = "منذ شهر"
                else:
                    last_activity_display = f"منذ {months} أشهر"
        else:
            last_activity_display = "غير محدد"

        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "avatar_url": avatar_url,
            "total_requests": user_request_stats.get("total_requests", 0),
            "pending_requests": user_request_stats.get("pending", 0),
            "completed_requests": user_request_stats.get("completed", 0),
            "in_progress_requests": user_request_stats.get("in_progress", 0),
            "rejected_requests": user_request_stats.get("rejected", 0),
            "last_activity": last_activity_display,
            "last_activity_time": last_activity.created_at if last_activity else None
        }
        users_with_data.append(user_dict)

    # Calculate summary statistics
    total_users = len(users_with_data)
    active_users = len([u for u in users_with_data if u["is_active"]])
    admin_users = len([u for u in users_with_data if u["role"] == UserRole.ADMIN])
    total_requests = sum(u["total_requests"] for u in users_with_data)

    return templates.TemplateResponse(
        "admin/users_table_new.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users_with_data,
            "total_users": total_users,
            "active_users": active_users,
            "admin_users": admin_users,
            "total_requests": total_requests
        }
    )


@router.get("/api/requests/{request_id}/files", response_class=JSONResponse)
async def get_request_files_api(
    request: Request,
    request_id: int,
    db: Session = Depends(get_db)
):
    """API endpoint to get files for a specific request"""
    try:
        # Get current user for permission check
        current_user = await get_current_user_cookie(request, db)

        # Get the request
        req = RequestService.get_request_by_id(db, request_id)
        if not req:
            return JSONResponse(
                status_code=404,
                content={"error": "Request not found"}
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
                description=f"تم الوصول إلى ملفات الطلب {req.request_number} عبر API بواسطة {current_user.full_name or current_user.username}",
                request=request,
                details={
                    "request_id": req.id,
                    "request_number": req.request_number,
                    "action": "api_files_access"
                }
            )

        # Get files
        files_data = []
        for file in req.files:
            files_data.append({
                "id": file.id,
                "original_filename": file.original_filename,
                "stored_filename": file.stored_filename,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "mime_type": file.mime_type,
                "file_category": file.file_category,
                "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else None
            })

        return JSONResponse(content={"files": files_data})

    except Exception as e:
        logger.error(f"Error getting request files: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


@router.get("/requests/{request_id}")
async def redirect_admin_request_view(request_id: int):
    """Redirect old admin request URLs to the correct view URL"""
    return RedirectResponse(url=f"/admin/requests/{request_id}/view", status_code=301)


@router.get("/requests/{request_id}/view", response_class=HTMLResponse)
async def view_request_admin(
    request: Request,
    request_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """View request details in admin panel"""
    # Get the request
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Get request owner
    request_owner = UserService.get_user_by_id(db, req.user_id)

    # Get request statistics
    request_stats = RequestService.get_user_request_statistics(db, req.user_id)

    return templates.TemplateResponse(
        "requests/view_request.html",
        {
            "request": request,
            "current_user": current_user,
            "req": req,
            "request_owner": request_owner,
            "request_stats": request_stats,
            "is_admin_view": True
        }
    )


@router.get("/requests/{request_id}/files", response_class=HTMLResponse)
async def manage_request_files_admin(
    request: Request,
    request_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Manage files for a specific request in admin panel"""
    # Get the request
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Get request owner
    request_owner = UserService.get_user_by_id(db, req.user_id)

    # Get request statistics
    request_stats = RequestService.get_user_request_statistics(db, req.user_id)

    return templates.TemplateResponse(
        "admin/manage_files.html",
        {
            "request": request,
            "current_user": current_user,
            "req": req,
            "request_owner": request_owner,
            "request_stats": request_stats,
            "is_admin_view": True
        }
    )


@router.get("/requests/{request_id}/edit", response_class=HTMLResponse)
async def edit_request_admin(
    request: Request,
    request_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Edit request in admin panel"""
    # Get the request
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Get request owner
    request_owner = UserService.get_user_by_id(db, req.user_id)

    return templates.TemplateResponse(
        "admin/edit_request.html",
        {
            "request": request,
            "current_user": current_user,
            "req": req,
            "request_owner": request_owner,
            "statuses": [s.value for s in RequestStatus]
        }
    )


@router.delete("/requests/{request_id}")
async def delete_request_admin(
    request_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Delete request - Admin only"""
    # Get the request to verify it exists
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Log the deletion attempt
    logger.info(f"Admin {current_user.username} attempting to delete request {request_id}")

    # Delete the request
    success = RequestService.delete_request(db, request_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete request")

    # Log successful deletion
    logger.info(f"Admin {current_user.username} successfully deleted request {request_id}")

    return {"success": True, "message": "Request deleted successfully"}


@router.post("/requests/{request_id}/delete")
async def delete_request_admin_post(
    request_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Delete request via POST - Admin only (for form submission)"""
    # Get the request to verify it exists
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Log the deletion attempt
    logger.info(f"Admin {current_user.username} attempting to delete request {request_id}")

    # Delete the request
    success = RequestService.delete_request(db, request_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete request")

    # Log successful deletion
    logger.info(f"Admin {current_user.username} successfully deleted request {request_id}")

    return RedirectResponse(url="/admin/requests?message=Request deleted successfully", status_code=303)


@router.post("/requests/{request_id}/edit")
async def update_request_admin(
    request: Request,
    request_id: int,
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
    # Status and Notes
    status: str = Form(...),
    admin_notes: Optional[str] = Form(None),
    # File Uploads (optional - for adding new files)
    architectural_plans: List[UploadFile] = FastAPIFile(None),
    electrical_mechanical_plans: List[UploadFile] = FastAPIFile(None),
    inspection_department: List[UploadFile] = FastAPIFile(None),
    fire_equipment_files: List[UploadFile] = FastAPIFile(None),
    commercial_records_files: List[UploadFile] = FastAPIFile(None),
    engineering_offices_files: List[UploadFile] = FastAPIFile(None),
    hazardous_materials_files: List[UploadFile] = FastAPIFile(None),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Update request with all fields in admin panel"""
    try:
        # Get the request
        req = RequestService.get_request_by_id(db, request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")

        # Validate status
        try:
            new_status = RequestStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")

        # Validate personal number (9 digits exactly)
        if personal_number and len(personal_number) != 9:
            return RedirectResponse(
                url=f"/admin/requests/{request_id}/edit?error=الرقم الشخصي يجب أن يكون 9 أرقام بالضبط",
                status_code=303
            )

        # Store old values for logging
        old_status = req.status
        changes = []

        # Update personal information
        if req.full_name != full_name:
            changes.append(f"الاسم: {req.full_name} → {full_name}")
            req.full_name = full_name

        if req.personal_number != personal_number:
            changes.append(f"الرقم الشخصي: {req.personal_number} → {personal_number}")
            req.personal_number = personal_number

        if req.phone_number != phone_number:
            changes.append(f"رقم الهاتف: {req.phone_number} → {phone_number}")
            req.phone_number = phone_number

        # Update building information
        if req.building_name != building_name:
            changes.append(f"رقم المبنى: {req.building_name} → {building_name}")
            req.building_name = building_name

        if req.road_name != road_name:
            changes.append(f"اسم الطريق: {req.road_name} → {road_name}")
            req.road_name = road_name

        if req.building_number != building_number:
            changes.append(f"رقم المبنى: {req.building_number} → {building_number}")
            req.building_number = building_number

        if req.civil_defense_file_number != civil_defense_file_number:
            changes.append(f"رقم ملف الدفاع المدني: {req.civil_defense_file_number} → {civil_defense_file_number}")
            req.civil_defense_file_number = civil_defense_file_number

        if req.building_permit_number != building_permit_number:
            changes.append(f"رقم إجازة البناء: {req.building_permit_number} → {building_permit_number}")
            req.building_permit_number = building_permit_number

        # Update license sections
        if req.licenses_section != licenses_section:
            changes.append(f"قسم التراخيص: {req.licenses_section} → {licenses_section}")
            req.licenses_section = licenses_section

        if req.fire_equipment_section != fire_equipment_section:
            changes.append(f"قسم معدات الحريق: {req.fire_equipment_section} → {fire_equipment_section}")
            req.fire_equipment_section = fire_equipment_section

        if req.commercial_records_section != commercial_records_section:
            changes.append(f"قسم السجلات التجارية: {req.commercial_records_section} → {commercial_records_section}")
            req.commercial_records_section = commercial_records_section

        if req.engineering_offices_section != engineering_offices_section:
            changes.append(f"قسم المكاتب الهندسية: {req.engineering_offices_section} → {engineering_offices_section}")
            req.engineering_offices_section = engineering_offices_section

        if req.hazardous_materials_section != hazardous_materials_section:
            changes.append(f"قسم المواد الخطرة: {req.hazardous_materials_section} → {hazardous_materials_section}")
            req.hazardous_materials_section = hazardous_materials_section

        # Update status
        if req.status != new_status:
            changes.append(f"الحالة: {req.status.value} → {new_status.value}")
            req.status = new_status

        # Add admin notes
        if admin_notes:
            if req.description:
                req.description += f"\n\nملاحظات المدير ({current_user.full_name or current_user.username}): {admin_notes}"
            else:
                req.description = f"ملاحظات المدير ({current_user.full_name or current_user.username}): {admin_notes}"
            changes.append("تم إضافة ملاحظات المدير")

        # Handle file uploads
        uploaded_files_count = 0
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
                        file_result = await RequestService.add_files_to_request(
                            db=db,
                            request_id=req.id,
                            files=valid_files,
                            category=category
                        )
                        uploaded_files_count += len(file_result.get("saved_files", []))
                    except Exception as e:
                        logger.error(f"Error uploading files for category {category}: {e}")

        if uploaded_files_count > 0:
            changes.append(f"تم رفع {uploaded_files_count} ملف جديد")

        # Commit changes
        db.commit()

        # Log activity
        from app.services.activity_service import ActivityService
        ActivityService.log_activity(
            db=db,
            user_id=req.user_id,
            activity_type="request_updated",
            description=f"تم تحديث الطلب {req.request_number} بواسطة المدير",
            details={
                "request_id": req.id,
                "request_number": req.request_number,
                "changes": changes,
                "updated_by_admin": current_user.id,
                "admin_notes": admin_notes,
                "uploaded_files": uploaded_files_count
            }
        )

        success_message = f"تم تحديث الطلب بنجاح"
        if changes:
            success_message += f" ({len(changes)} تغيير)"
        if uploaded_files_count > 0:
            success_message += f" مع رفع {uploaded_files_count} ملف جديد"

        return RedirectResponse(
            url=f"/admin/requests/{request_id}/view?success={success_message}",
            status_code=303
        )

    except Exception as e:
        logger.error(f"Error updating request {request_id}: {e}")
        return RedirectResponse(
            url=f"/admin/requests/{request_id}/edit?error=حدث خطأ أثناء تحديث الطلب: {str(e)}",
            status_code=303
        )


@router.delete("/api/files/{file_id}/delete")
async def delete_file_admin(
    file_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Delete a file (admin only)"""
    try:
        from app.models.file import File
        from app.services.activity_service import ActivityService

        # Get the file
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "File not found"}
            )

        # Store file info for logging
        file_info = {
            "id": file.id,
            "original_filename": file.original_filename,
            "file_category": file.file_category,
            "request_id": file.request_id
        }

        # Delete the file using RequestService
        success = RequestService.delete_file_from_request(db, file_id)

        if success:
            # Log the deletion activity
            try:
                ActivityService.log_activity(
                    db=db,
                    user_id=file_info["request_id"],  # Use request owner's ID
                    activity_type="file_deleted",
                    description=f"تم حذف الملف {file_info['original_filename']} بواسطة المدير",
                    details={
                        "file_id": file_info["id"],
                        "filename": file_info["original_filename"],
                        "category": file_info["file_category"],
                        "deleted_by_admin": current_user.id,
                        "admin_name": current_user.full_name or current_user.username
                    }
                )
            except Exception as log_error:
                logger.warning(f"Failed to log file deletion activity: {log_error}")

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
        logger.error(f"Error deleting file {file_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/users/{user_id}/approve")
async def approve_user_from_users_page(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Approve a user account from the users page"""
    try:
        # Get the user
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            return RedirectResponse(
                url="/admin/users?error=المستخدم غير موجود",
                status_code=303
            )

        # Check if user is pending approval
        if user.approval_status != UserStatus.PENDING:
            return RedirectResponse(
                url="/admin/users?error=المستخدم ليس في انتظار الموافقة",
                status_code=303
            )

        # Update user status
        user.approval_status = UserStatus.APPROVED
        user.is_active = True
        db.commit()

        # Create approval notification for the user
        from app.services.notification_service import NotificationService
        try:
            NotificationService.create_user_approval_notification(
                db=db,
                user_id=user.id,
                admin_user_id=current_user.id,
                approved=True
            )
        except Exception as e:
            logger.warning(f"Failed to create approval notification for user {user.id}: {e}")

        # Log activity
        from app.utils.request_utils import log_user_activity
        log_user_activity(
            db=db,
            user_id=current_user.id,
            activity_type="user_approved",
            description=f"Admin approved user: {user.username}",
            request=request
        )

        return RedirectResponse(
            url="/admin/users?success=تم قبول المستخدم بنجاح",
            status_code=303
        )

    except Exception as e:
        logger.error(f"Error approving user {user_id}: {e}")
        return RedirectResponse(
            url="/admin/users?error=فشل في قبول المستخدم",
            status_code=303
        )


@router.post("/users/{user_id}/reject")
async def reject_user_from_users_page(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Reject a user account from the users page"""
    try:
        # Get the user
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            return RedirectResponse(
                url="/admin/users?error=المستخدم غير موجود",
                status_code=303
            )

        # Check if user is pending approval
        if user.approval_status != UserStatus.PENDING:
            return RedirectResponse(
                url="/admin/users?error=المستخدم ليس في انتظار الموافقة",
                status_code=303
            )

        # Update user status
        user.approval_status = UserStatus.REJECTED
        user.is_active = False
        db.commit()

        # Create rejection notification for the user
        from app.services.notification_service import NotificationService
        try:
            NotificationService.create_user_approval_notification(
                db=db,
                user_id=user.id,
                admin_user_id=current_user.id,
                approved=False
            )
        except Exception as e:
            logger.warning(f"Failed to create rejection notification for user {user.id}: {e}")

        # Log activity
        from app.utils.request_utils import log_user_activity
        log_user_activity(
            db=db,
            user_id=current_user.id,
            activity_type="user_rejected",
            description=f"Admin rejected user: {user.username}",
            request=request
        )

        return RedirectResponse(
            url="/admin/users?success=تم رفض المستخدم بنجاح",
            status_code=303
        )

    except Exception as e:
        logger.error(f"Error rejecting user {user_id}: {e}")
        return RedirectResponse(
            url="/admin/users?error=فشل في رفض المستخدم",
            status_code=303
        )


@router.get("/users/new", response_class=HTMLResponse)
async def new_user_form(
    request: Request,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Display new user creation form"""
    # Get user statistics for sidebar
    all_users = UserService.get_all_users(db, limit=1000)
    total_users = len(all_users)
    admin_count = len([u for u in all_users if u.role == UserRole.ADMIN])
    user_count = len([u for u in all_users if u.role == UserRole.USER])
    active_users = len([u for u in all_users if u.is_active])

    return templates.TemplateResponse(
        "admin/new_user.html",
        {
            "request": request,
            "current_user": current_user,
            "roles": [role.value for role in UserRole],
            "total_users": total_users,
            "admin_count": admin_count,
            "user_count": user_count,
            "active_users": active_users
        }
    )


@router.post("/users/new")
async def create_new_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Create new user"""
    try:
        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError:
            return templates.TemplateResponse(
                "admin/new_user.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "roles": [role.value for role in UserRole],
                    "error": "Invalid role selected"
                },
                status_code=400
            )

        # Create user
        new_user = UserService.create_user(
            db=db,
            username=username,
            email=email,
            full_name=full_name,
            password=password,
            role=user_role
        )

        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.PROFILE_UPDATED,
            description=f"Admin created new user: {username} with role {role}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        users = UserService.get_all_users(db, limit=100)
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "success": f"User {username} created successfully"
            }
        )

    except HTTPException as e:
        return templates.TemplateResponse(
            "admin/new_user.html",
            {
                "request": request,
                "current_user": current_user,
                "roles": [role.value for role in UserRole],
                "error": e.detail,
                "form_data": {
                    "username": username,
                    "email": email,
                    "full_name": full_name,
                    "role": role
                }
            },
            status_code=400
        )


@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Toggle user active status"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Don't allow deactivating self
    if user.id == current_user.id:
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": UserService.get_all_users(db, limit=100),
                "error": "Cannot deactivate your own account"
            },
            status_code=400
        )

    # Toggle status
    UserService.update_user(db, user_id, is_active=not user.is_active)

    # Log activity
    action = "activated" if not user.is_active else "deactivated"
    UserService.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=ActivityType.PROFILE_UPDATED,
        description=f"Admin {action} user: {user.username}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    users = UserService.get_all_users(db, limit=100)
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users,
            "success": f"User {user.username} has been {action}"
        }
    )


@router.post("/users/{user_id}/update-role")
async def update_user_role(
    request: Request,
    user_id: int,
    role: str = Form(...),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Update user role"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Don't allow changing own role
    if user.id == current_user.id:
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": UserService.get_all_users(db, limit=100),
                "error": "Cannot change your own role"
            },
            status_code=400
        )

    # Validate role
    try:
        new_role = UserRole(role)
    except ValueError:
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": UserService.get_all_users(db, limit=100),
                "error": "Invalid role selected"
            },
            status_code=400
        )

    # Update role
    UserService.update_user(db, user_id, role=new_role)

    # Log activity
    UserService.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=ActivityType.PROFILE_UPDATED,
        description=f"Admin changed user {user.username} role to {new_role.value}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    users = UserService.get_all_users(db, limit=100)
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users,
            "success": f"User {user.username} role updated to {new_role.value}"
        }
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Display user edit form"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Get user avatar URL
    from app.services.avatar_service import AvatarService
    user_avatar_url = AvatarService.get_avatar_url(user.id, user.full_name, db)

    return templates.TemplateResponse(
        "admin/edit_user.html",
        {
            "request": request,
            "current_user": current_user,
            "user": user,
            "user_avatar_url": user_avatar_url,
            "roles": [role.value for role in UserRole]
        }
    )


@router.post("/users/{user_id}/edit")
async def update_user_profile(
    request: Request,
    user_id: int,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    is_active: bool = Form(False),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Don't allow editing own account through this interface
    if user.id == current_user.id:
        return templates.TemplateResponse(
            "admin/edit_user.html",
            {
                "request": request,
                "current_user": current_user,
                "user": user,
                "roles": [role.value for role in UserRole],
                "error": "Cannot edit your own account through this interface"
            },
            status_code=400
        )

    try:
        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError:
            return templates.TemplateResponse(
                "admin/edit_user.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "user": user,
                    "roles": [role.value for role in UserRole],
                    "error": "Invalid role selected"
                },
                status_code=400
            )

        # Update user
        updated_user = UserService.update_user(
            db=db,
            user_id=user_id,
            username=username,
            email=email,
            full_name=full_name,
            role=user_role,
            is_active=is_active
        )

        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.PROFILE_UPDATED,
            description=f"Admin updated user profile: {username}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        users = UserService.get_all_users(db, limit=100)
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "success": f"User {username} profile updated successfully"
            }
        )

    except HTTPException as e:
        return templates.TemplateResponse(
            "admin/edit_user.html",
            {
                "request": request,
                "current_user": current_user,
                "user": user,
                "roles": [role.value for role in UserRole],
                "error": e.detail
            },
            status_code=400
        )


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    request: Request,
    user_id: int,
    new_password: str = Form(...),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Reset user password"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Don't allow resetting own password through this interface
    if user.id == current_user.id:
        return templates.TemplateResponse(
            "admin/edit_user.html",
            {
                "request": request,
                "current_user": current_user,
                "user": user,
                "roles": [role.value for role in UserRole],
                "error": "Cannot reset your own password through this interface"
            },
            status_code=400
        )

    # Reset password
    success = UserService.change_password(db, user_id, new_password)

    if not success:
        return templates.TemplateResponse(
            "admin/edit_user.html",
            {
                "request": request,
                "current_user": current_user,
                "user": user,
                "roles": [role.value for role in UserRole],
                "error": "Failed to reset password"
            },
            status_code=500
        )

    # Log activity
    UserService.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=ActivityType.PROFILE_UPDATED,
        description=f"Admin reset password for user: {user.username}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return templates.TemplateResponse(
        "admin/edit_user.html",
        {
            "request": request,
            "current_user": current_user,
            "user": user,
            "roles": [role.value for role in UserRole],
            "success": f"Password reset successfully for user {user.username}"
        }
    )


@router.post("/users/{user_id}/soft-delete")
async def soft_delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Soft delete user (deactivate)"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Don't allow soft deleting self
    if user.id == current_user.id:
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": UserService.get_all_users(db, limit=100),
                "error": "Cannot delete your own account"
            },
            status_code=400
        )

    # Soft delete user
    success = UserService.soft_delete_user(db, user_id)

    if success:
        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.PROFILE_UPDATED,
            description=f"Admin soft deleted user: {user.username}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

    users = UserService.get_all_users(db, limit=100)
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users,
            "success": f"User {user.username} has been deactivated" if success else None,
            "error": "Failed to deactivate user" if not success else None
        }
    )



@router.get("/archived-requests", response_class=HTMLResponse)
async def view_archived_requests(
    request: Request,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """View archived requests with search functionality"""
    archived_requests = RequestService.get_archived_requests(
        db,
        limit=100,
        search_query=search
    )

    return templates.TemplateResponse(
        "admin/archived_requests.html",
        {
            "request": request,
            "current_user": current_user,
            "requests": archived_requests,
            "current_search": search
        }
    )


@router.get("/archive", response_class=HTMLResponse)
async def view_archive(
    request: Request,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """View archived requests with search functionality (alias for /archived-requests)"""
    archived_requests = RequestService.get_archived_requests(
        db,
        limit=100,
        search_query=search
    )

    return templates.TemplateResponse(
        "admin/archived_requests.html",
        {
            "request": request,
            "current_user": current_user,
            "requests": archived_requests,
            "current_search": search
        }
    )


@router.post("/requests/{request_id}/archive")
async def archive_request(
    request: Request,
    request_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Archive request"""
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Archive request
    success = RequestService.archive_request(db, request_id)

    if success:
        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.REQUEST_UPDATED,
            description=f"Admin archived request {req.request_number}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

    requests = RequestService.get_all_requests(db, limit=100)
    return templates.TemplateResponse(
        "admin/requests.html",
        {
            "request": request,
            "current_user": current_user,
            "requests": requests,
            "success": f"Request {req.request_number} has been archived" if success else None,
            "error": "Failed to archive request" if not success else None
        }
    )


@router.post("/requests/{request_id}/restore")
async def restore_request(
    request: Request,
    request_id: int,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Restore archived request"""
    req = RequestService.get_request_by_id(db, request_id)
    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )

    # Restore request
    success = RequestService.restore_request(db, request_id)

    if success:
        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.REQUEST_UPDATED,
            description=f"Admin restored request {req.request_number}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

    archived_requests = RequestService.get_archived_requests(db, limit=100)
    return templates.TemplateResponse(
        "admin/archived_requests.html",
        {
            "request": request,
            "current_user": current_user,
            "requests": archived_requests,
            "current_search": None,
            "success": f"Request {req.request_number} has been restored" if success else None,
            "error": "Failed to restore request" if not success else None
        }
    )


@router.post("/users/bulk-action")
async def bulk_user_action(
    request: Request,
    action: str = Form(...),
    user_ids: List[int] = Form(...),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Perform bulk action on users"""
    if not user_ids:
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": UserService.get_all_users(db, limit=100),
                "error": "لم يتم اختيار أي مستخدمين"
            },
            status_code=400
        )

    # Don't allow bulk actions on self
    if current_user.id in user_ids:
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": UserService.get_all_users(db, limit=100),
                "error": "لا يمكن تطبيق العمليات المجمعة على حسابك الشخصي"
            },
            status_code=400
        )

    success_count = 0
    total_count = len(user_ids)

    try:
        for user_id in user_ids:
            user = UserService.get_user_by_id(db, user_id)
            if not user or user.id == current_user.id:
                continue

            if action == "activate":
                UserService.update_user(db, user_id, is_active=True)
                success_count += 1
            elif action == "deactivate":
                UserService.update_user(db, user_id, is_active=False)
                success_count += 1
            elif action == "make_admin":
                UserService.update_user(db, user_id, role=UserRole.ADMIN)
                success_count += 1
            elif action == "make_user":
                UserService.update_user(db, user_id, role=UserRole.USER)
                success_count += 1

        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.PROFILE_UPDATED,
            description=f"Admin performed bulk action '{action}' on {success_count} users",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        action_names = {
            "activate": "تفعيل",
            "deactivate": "إلغاء تفعيل",
            "make_admin": "ترقية إلى مدير",
            "make_user": "تحويل إلى مستخدم عادي"
        }

        users = UserService.get_all_users(db, limit=100)
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "success": f"تم {action_names.get(action, action)} {success_count} من أصل {total_count} مستخدم"
            }
        )

    except Exception as e:
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": UserService.get_all_users(db, limit=100),
                "error": f"حدث خطأ أثناء تنفيذ العملية: {str(e)}"
            },
            status_code=500
        )


@router.post("/requests/bulk-action")
async def bulk_request_action(
    request: Request,
    action: str = Form(...),
    request_ids: List[int] = Form(...),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Perform bulk action on requests"""
    if not request_ids:
        return templates.TemplateResponse(
            "admin/requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": RequestService.get_all_requests(db, limit=100),
                "statuses": [s.value for s in RequestStatus],
                "error": "لم يتم اختيار أي طلبات"
            },
            status_code=400
        )

    success_count = 0
    total_count = len(request_ids)

    try:
        for request_id in request_ids:
            req = RequestService.get_request_by_id(db, request_id)
            if not req:
                continue

            if action == "pending":
                RequestService.update_request(db, request_id, status=RequestStatus.PENDING)
                success_count += 1
            elif action == "in_progress":
                RequestService.update_request(db, request_id, status=RequestStatus.IN_PROGRESS)
                success_count += 1
            elif action == "completed":
                RequestService.update_request(db, request_id, status=RequestStatus.COMPLETED)
                success_count += 1
            elif action == "rejected":
                RequestService.update_request(db, request_id, status=RequestStatus.REJECTED)
                success_count += 1
            elif action == "archive":
                RequestService.archive_request(db, request_id)
                success_count += 1

        # Log activity
        UserService.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.REQUEST_UPDATED,
            description=f"Admin performed bulk action '{action}' on {success_count} requests",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        action_names = {
            "pending": "تحويل إلى قيد المراجعة",
            "in_progress": "تحويل إلى قيد التنفيذ",
            "completed": "تحويل إلى مكتمل",
            "rejected": "تحويل إلى مرفوض",
            "archive": "أرشفة"
        }

        requests = RequestService.get_all_requests(db, limit=100)
        return templates.TemplateResponse(
            "admin/requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": requests,
                "statuses": [s.value for s in RequestStatus],
                "success": f"تم {action_names.get(action, action)} {success_count} من أصل {total_count} طلب"
            }
        )

    except Exception as e:
        return templates.TemplateResponse(
            "admin/requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": RequestService.get_all_requests(db, limit=100),
                "statuses": [s.value for s in RequestStatus],
                "error": f"حدث خطأ أثناء تنفيذ العملية: {str(e)}"
            },
            status_code=500
        )


@router.get("/requests-records", response_class=HTMLResponse)
async def admin_requests_records(
    request: Request,
    user_id: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=100),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Admin requests records page - track all user interactions with requests"""
    try:
        # Calculate pagination
        skip = (page - 1) * per_page

        # Convert empty strings to None and parse user_id
        user_id_int = None
        if user_id and user_id.strip():
            try:
                user_id_int = int(user_id)
            except ValueError:
                user_id_int = None

        # Convert empty strings to None for other parameters
        activity_type = activity_type if activity_type and activity_type.strip() else None
        date_from = date_from if date_from and date_from.strip() else None
        date_to = date_to if date_to and date_to.strip() else None
        search = search if search and search.strip() else None

        # Get all users for filter dropdown
        all_users = UserService.get_all_users(db, limit=1000)

        # Get activities based on filters
        if user_id_int:
            # Get activities for specific user
            activities = ActivityService.get_user_activities(
                db=db,
                user_id=user_id_int,
                activity_type=activity_type,
                date_from=date_from,
                date_to=date_to,
                limit=per_page,
                skip=skip
            )

            # Get user statistics
            user_stats = ActivityService.get_user_activity_statistics(db, user_id_int)
            target_user = UserService.get_user_by_id(db, user_id_int)
        else:
            # Get all activities across all users
            activities = ActivityService.get_all_activities(
                db=db,
                activity_type=activity_type,
                date_from=date_from,
                date_to=date_to,
                search_query=search,
                limit=per_page,
                skip=skip
            )
            user_stats = None
            target_user = None

        # Get comprehensive system statistics
        system_stats = ActivityService.get_system_activity_statistics(db)

        # Get activity type options
        activity_types = [
            {'value': 'request_created', 'label': 'إنشاء طلب'},
            {'value': 'request_updated', 'label': 'تحديث طلب'},
            {'value': 'request_completed', 'label': 'إكمال طلب'},
            {'value': 'request_rejected', 'label': 'رفض طلب'},
            {'value': 'file_uploaded', 'label': 'رفع ملف'},
            {'value': 'file_deleted', 'label': 'حذف ملف'},
            {'value': 'login', 'label': 'تسجيل دخول'},
            {'value': 'profile_updated', 'label': 'تحديث الملف الشخصي'},
            {'value': 'avatar_uploaded', 'label': 'رفع صورة شخصية'}
        ]

        # Calculate pagination info
        total_activities = len(activities) if len(activities) < per_page else (page * per_page) + 1
        has_next = len(activities) == per_page
        has_prev = page > 1

        return templates.TemplateResponse(
            "admin/requests_records.html",
            {
                "request": request,
                "current_user": current_user,
                "activities": activities,
                "all_users": all_users,
                "target_user": target_user,
                "user_stats": user_stats,
                "activity_types": activity_types,
                "filters": {
                    "user_id": user_id_int,
                    "activity_type": activity_type,
                    "date_from": date_from,
                    "date_to": date_to,
                    "search": search
                },
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "has_next": has_next,
                    "has_prev": has_prev,
                    "total": total_activities
                },
                "system_stats": system_stats
            }
        )

    except Exception as e:
        logging.error(f"Error in admin requests records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/debug-data")
async def debug_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_cookie)
):
    """Debug endpoint to check database data"""
    try:
        from app.models import Request as RequestModel

        # Count users
        user_count = db.query(User).count()
        active_user_count = db.query(User).filter(User.is_active == True).count()

        # Count requests
        request_count = db.query(RequestModel).count()

        # Get sample users
        sample_users = db.query(User).limit(5).all()

        # Get sample requests
        sample_requests = db.query(RequestModel).limit(5).all()

        return {
            "user_count": user_count,
            "active_user_count": active_user_count,
            "request_count": request_count,
            "sample_users": [{"id": u.id, "username": u.username, "email": u.email, "is_active": u.is_active} for u in sample_users],
            "sample_requests": [{"id": r.id, "user_id": r.user_id, "status": r.status.value if r.status else None, "created_at": r.created_at.isoformat()} for r in sample_requests]
        }
    except Exception as e:
        return {"error": str(e)}


async def generate_pdf_report(report_data: dict, period: int) -> Response:
    """Generate PDF report with Arabic language support"""
    try:
        # datetime already imported as dt above

        # Create a BytesIO buffer to hold the PDF
        buffer = io.BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)

        # Container for the 'Flowable' objects
        story = []

        # Define styles
        styles = getSampleStyleSheet()

        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        # Normal text style
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )

        # Header style
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )

        # Add title
        title = Paragraph("User Activity Report", title_style)
        story.append(title)
        story.append(Spacer(1, 20))

        # Add report period info
        period_text = f"Report Period: {period} months"
        story.append(Paragraph(period_text, normal_style))
        story.append(Spacer(1, 10))

        # Add generation date
        gen_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_text = f"Generated: {gen_date}"
        story.append(Paragraph(date_text, normal_style))
        story.append(Spacer(1, 20))

        # Add summary statistics
        story.append(Paragraph("Summary Statistics", header_style))

        summary_data = [
            ['Metric', 'Value'],
            ['Total Users', str(report_data.get('total_users', 0))],
            ['Active Users', str(report_data.get('active_users', 0))],
            ['Inactive Users', str(report_data.get('inactive_users', 0))],
            ['Total Requests', str(report_data.get('total_requests', 0))],
            ['Avg Requests per User', str(report_data.get('average_requests_per_user', 0))]
        ]

        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 30))

        # Add user details
        story.append(Paragraph("User Details", header_style))

        # Prepare user data for table
        user_data = [['User', 'Email', 'Total Requests', 'Daily Avg', 'Activity Level']]

        user_reports = report_data.get('user_reports', [])
        for user in user_reports[:20]:  # Limit to first 20 users for PDF
            user_data.append([
                user.get('name', ''),
                user.get('email', ''),
                str(user.get('total_requests', 0)),
                str(user.get('daily_average', 0)),
                user.get('activity_level', '')
            ])

        if len(user_reports) > 20:
            user_data.append(['...', f'and {len(user_reports) - 20} more users', '', '', ''])

        user_table = Table(user_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1*inch, 1.5*inch])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(user_table)

        # Build PDF
        doc.build(story)

        # Get the value of the BytesIO buffer and return as response
        pdf_data = buffer.getvalue()
        buffer.close()

        # Create filename with current date
        filename = f"user_activity_report_{period}months_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF report: {str(e)}")


async def generate_html_report(report_data: dict, period: int) -> Response:
    """Generate HTML report with proper Arabic language support"""
    try:
        # datetime already imported as dt above

        # Generate HTML content for the report
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>حركة المستخدمين</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;700&display=swap');

                body {{
                    font-family: 'Noto Sans Arabic', Arial, sans-serif;
                    direction: rtl;
                    text-align: right;
                    margin: 20px;
                    line-height: 1.6;
                    background-color: #f8f9fa;
                }}

                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }}

                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding: 30px 20px;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}

                .title {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #1f2937;
                    margin-bottom: 10px;
                }}

                .subtitle {{
                    font-size: 16px;
                    color: #6b7280;
                    margin-bottom: 5px;
                }}

                .summary-section {{
                    margin-bottom: 40px;
                }}

                .section-title {{
                    font-size: 22px;
                    font-weight: bold;
                    color: #1f2937;
                    margin-bottom: 20px;
                    border-bottom: 1px solid #e5e7eb;
                    padding-bottom: 10px;
                }}

                .summary-table, .user-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                    font-size: 14px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}

                .summary-table th, .summary-table td,
                .user-table th, .user-table td {{
                    border: 1px solid #dee2e6;
                    padding: 12px;
                    text-align: center;
                }}

                .summary-table th, .user-table th {{
                    background-color: #f9fafb;
                    color: #374151;
                    font-weight: bold;
                    border-bottom: 2px solid #e5e7eb;
                }}

                .summary-table tr:nth-child(even),
                .user-table tr:nth-child(even) {{
                    background-color: #f8f9fa;
                }}

                .activity-high {{
                    color: #28a745;
                    font-weight: bold;
                    background-color: #d4edda;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
                .activity-medium {{
                    color: #ffc107;
                    font-weight: bold;
                    background-color: #fff3cd;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
                .activity-low {{
                    color: #fd7e14;
                    font-weight: bold;
                    background-color: #ffeaa7;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
                .activity-none {{
                    color: #6c757d;
                    background-color: #e9ecef;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}

                .print-button {{
                    position: fixed;
                    top: 20px;
                    left: 20px;
                    background-color: #374151;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    z-index: 1000;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}

                .print-button:hover {{
                    background-color: #1f2937;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.15);
                }}

                @media print {{
                    .print-button {{ display: none; }}
                    body {{ margin: 0; background-color: white; }}
                    .container {{ box-shadow: none; }}
                }}
            </style>
        </head>
        <body>
            <button class="print-button" onclick="window.print()">طباعة التقرير</button>

            <div class="container">
                <div class="header">
                    <div class="title">حركة المستخدمين</div>
                    <div class="subtitle">فترة التقرير: {period} أشهر</div>
                    <div class="subtitle">تاريخ الإنشاء: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
        """

        # Add summary statistics section
        html_content += f"""
                <div class="summary-section">
                    <div class="section-title">ملخص الإحصائيات</div>
                    <table class="summary-table">
                        <tr>
                            <th>المؤشر</th>
                            <th>القيمة</th>
                        </tr>
                        <tr>
                            <td>إجمالي المستخدمين</td>
                            <td>{report_data.get('total_users', 0)}</td>
                        </tr>
                        <tr>
                            <td>المستخدمون النشطون</td>
                            <td>{report_data.get('active_users', 0)}</td>
                        </tr>
                        <tr>
                            <td>المستخدمون غير النشطين</td>
                            <td>{report_data.get('inactive_users', 0)}</td>
                        </tr>
                        <tr>
                            <td>إجمالي الطلبات</td>
                            <td>{report_data.get('total_requests', 0)}</td>
                        </tr>
                        <tr>
                            <td>متوسط الطلبات لكل مستخدم</td>
                            <td>{report_data.get('average_requests_per_user', 0):.2f}</td>
                        </tr>
                    </table>
                </div>
        """

        # Add user details section
        html_content += """
                <div class="section-title">تفاصيل المستخدمين</div>
                <table class="user-table">
                    <tr>
                        <th>المستخدم</th>
                        <th>البريد الإلكتروني</th>
                        <th>إجمالي الطلبات</th>
                        <th>المتوسط اليومي</th>
                        <th>مستوى النشاط</th>
                    </tr>
        """

        # Add user data rows
        user_reports = report_data.get('user_reports', [])
        for user in user_reports:
            activity_class = 'activity-none'
            activity_text = 'غير نشط'

            daily_avg = user.get('daily_average', 0)
            if daily_avg > 1:
                activity_class = 'activity-high'
                activity_text = 'نشط جداً'
            elif daily_avg > 0.5:
                activity_class = 'activity-medium'
                activity_text = 'نشط'
            elif daily_avg > 0.1:
                activity_class = 'activity-low'
                activity_text = 'نشط قليلاً'

            html_content += f"""
                    <tr>
                        <td>{user.get('name', '')}</td>
                        <td>{user.get('email', '')}</td>
                        <td>{user.get('total_requests', 0)}</td>
                        <td>{daily_avg:.2f}</td>
                        <td><span class="{activity_class}">{activity_text}</span></td>
                    </tr>
            """

        html_content += """
                </table>
            </div>
        </body>
        </html>
        """

        return Response(content=html_content, media_type="text/html")

    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating HTML report: {str(e)}")


@router.get("/user-activity-report", response_class=HTMLResponse)
async def user_activity_report(
    request: Request,
    period: int = Query(3, ge=1, le=24),  # Period in months, 1-24 months
    format: str = Query("html", regex="^(html|pdf|csv|arabic)$"),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Generate user activity report for specified period"""
    try:
        logger.info(f"Generating user activity report for period: {period} months")
        # Generate the report
        report_data = ActivityService.generate_user_activity_report(db, period_months=period)
        logger.info(f"Report generated successfully with {len(report_data.get('user_reports', []))} users")

        if format == "pdf":
            logger.info("Generating PDF format")
            return await generate_pdf_report(report_data, period)
        elif format == "arabic":
            logger.info("Generating Arabic HTML format")
            return await generate_html_report(report_data, period)
        elif format == "csv":
            # Generate CSV response
            import io
            import csv
            logger.info("Generating CSV format")

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            writer.writerow([
                'اسم المستخدم', 'البريد الإلكتروني', 'إجمالي الطلبات',
                'متوسط الطلبات اليومية', 'متوسط الطلبات الأسبوعية',
                'متوسط الطلبات الشهرية', 'الطلبات الأخيرة (30 يوم)',
                'مستوى النشاط', 'أول طلب', 'آخر طلب'
            ])

            # Write data - use the version with datetime objects for proper formatting
            user_reports_to_export = report_data.get('user_reports_with_datetime', report_data.get('user_reports', []))
            for user_report in user_reports_to_export:
                # Handle datetime formatting for CSV
                first_request_str = ''
                last_request_str = ''

                if user_report.get('first_request_datetime'):
                    first_request_str = user_report['first_request_datetime'].strftime('%Y-%m-%d %H:%M')
                elif user_report.get('first_request_date'):
                    # If we only have the string version, use it directly
                    first_request_str = user_report['first_request_date']

                if user_report.get('last_request_datetime'):
                    last_request_str = user_report['last_request_datetime'].strftime('%Y-%m-%d %H:%M')
                elif user_report.get('last_request_date'):
                    # If we only have the string version, use it directly
                    last_request_str = user_report['last_request_date']

                writer.writerow([
                    user_report['name'],
                    user_report['email'],
                    user_report['total_requests'],
                    user_report['daily_average'],
                    user_report['weekly_average'],
                    user_report['monthly_average'],
                    user_report['recent_requests'],
                    user_report['activity_level'],
                    first_request_str,
                    last_request_str
                ])

            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=user_activity_report_{period}months.csv"}
            )

        # HTML format (default)
        return templates.TemplateResponse(
            "admin/user_activity_report.html",
            {
                "request": request,
                "current_user": current_user,
                "report_data": report_data,
                "selected_period": period,
                "period_options": [
                    {"value": 1, "label": "الشهر الماضي"},
                    {"value": 3, "label": "آخر 3 أشهر"},
                    {"value": 6, "label": "آخر 6 أشهر"},
                    {"value": 9, "label": "آخر 9 أشهر"},
                    {"value": 12, "label": "السنة الماضية"},
                    {"value": 18, "label": "آخر 18 شهر"},
                    {"value": 24, "label": "آخر سنتين"}
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error generating user activity report: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.get("/test-report", response_class=JSONResponse)
async def test_report(
    request: Request,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Test route for debugging"""
    try:
        logger.info("Test report route accessed")
        return JSONResponse(content={"status": "success", "message": "Test route working"})
    except Exception as e:
        logger.error(f"Error in test route: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@router.get("/requests", response_class=HTMLResponse)
async def manage_requests(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=10, le=100),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Manage requests page with search functionality and pagination"""
    import logging
    logger = logging.getLogger(__name__)

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = RequestStatus(status)
        except ValueError:
            pass

    # Calculate pagination
    skip = (page - 1) * per_page

    # Debug: Check total requests in database (including archived)
    try:
        total_all_requests = db.query(Request).count()
        total_non_archived = db.query(Request).filter(Request.is_archived == False).count()
        total_archived = db.query(Request).filter(Request.is_archived == True).count()

        logger.info(f"Admin requests debug - Total requests: {total_all_requests}, Non-archived: {total_non_archived}, Archived: {total_archived}")
        logger.info(f"Admin requests debug - Status filter: {status_filter}, Search: {search}, Page: {page}, Per page: {per_page}")
    except Exception as e:
        logger.error(f"Error checking request counts: {e}")

    # Get requests with pagination
    requests = RequestService.get_all_requests(
        db,
        skip=skip,
        limit=per_page,
        status=status_filter,
        search_query=search
    )

    # Get total count for pagination
    total_requests = RequestService.get_all_requests_count(
        db,
        status=status_filter,
        search_query=search
    )

    # Debug logging
    logger.info(f"Admin requests debug - Found {len(requests)} requests, Total count: {total_requests}")
    logger.info(f"Admin requests debug - Requests type: {type(requests)}")
    logger.info(f"Admin requests debug - Requests content: {[req.id if hasattr(req, 'id') else str(req) for req in requests] if requests else 'None'}")

    # Calculate pagination info
    total_pages = (total_requests + per_page - 1) // per_page

    template_context = {
        "request": request,
        "current_user": current_user,
        "requests": requests,
        "current_status": status,
        "current_search": search,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "total_requests": total_requests,
        "statuses": [s.value for s in RequestStatus]
    }

    logger.info(f"Admin requests debug - Template context requests: {len(template_context['requests']) if template_context['requests'] else 0}")

    return templates.TemplateResponse(
        "admin/requests.html",
        template_context
    )


@router.post("/requests/{request_id}/update-status")
async def update_request_status(
    request: Request,
    request_id: int,
    status: str = Form(...),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Update request status"""
    try:
        new_status = RequestStatus(status)
    except ValueError:
        return templates.TemplateResponse(
            "admin/requests.html",
            {
                "request": request,
                "current_user": current_user,
                "requests": RequestService.get_all_requests(db, limit=100),
                "error": "Invalid status"
            },
            status_code=400
        )
    
    req = RequestService.update_request_status(db, request_id, new_status, current_user.id)
    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "current_user": current_user},
            status_code=404
        )
    
    # Log activity
    UserService.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=ActivityType.REQUEST_UPDATED,
        description=f"Admin updated request {req.request_number} status to {new_status.value}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Redirect back to dashboard with success message
    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    return response


@router.get("/api/requests/load-more", response_class=HTMLResponse)
async def admin_load_more_requests(
    request: Request,
    skip: int = 10,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """HTMX endpoint to load more requests for admin dashboard"""
    # Load next batch of requests
    additional_requests = RequestService.get_all_requests(
        db, skip=skip, limit=10
    )

    return templates.TemplateResponse(
        "admin/partials/request_rows.html",
        {
            "request": request,
            "current_user": current_user,
            "recent_requests": additional_requests,
            "next_skip": skip + 10
        }
    )


def create_safe_db_session():
    """Create a safe database session with proper error handling"""
    from app.database import SessionLocal
    session = SessionLocal()
    try:
        # Test the connection with a simple query
        session.execute("SELECT 1")
        return session
    except Exception as e:
        logger.error(f"Failed to create safe database session: {e}")
        try:
            session.rollback()
            session.close()
        except:
            pass
        # Try again with a new session
        return SessionLocal()

@router.get("/activities/debug", response_class=HTMLResponse)
async def debug_activities(
    request: Request,
    current_user: User = Depends(require_admin_cookie)
):
    """Debug route to test activities without complex operations"""
    from app.models.activity import Activity, ActivityType

    debug_info = {
        "database_connection": "Unknown",
        "activities_table": "Unknown",
        "activities_count": 0,
        "activity_types": [],
        "sample_activities": []
    }

    fresh_db = None
    try:
        fresh_db = create_safe_db_session()
        debug_info["database_connection"] = "Success"

        # Test activities table
        try:
            count = fresh_db.query(Activity).count()
            debug_info["activities_table"] = "Exists"
            debug_info["activities_count"] = count
        except Exception as table_error:
            debug_info["activities_table"] = f"Error: {str(table_error)}"

        # Test activity types
        try:
            debug_info["activity_types"] = [t.value for t in ActivityType]
        except Exception as types_error:
            debug_info["activity_types"] = f"Error: {str(types_error)}"

        # Get sample activities
        try:
            sample_activities = fresh_db.query(Activity).limit(5).all()
            debug_info["sample_activities"] = [
                {
                    "id": a.id,
                    "user_id": a.user_id,
                    "activity_type": a.activity_type.value if a.activity_type else "Unknown",
                    "description": a.description,
                    "created_at": str(a.created_at)
                }
                for a in sample_activities
            ]
        except Exception as sample_error:
            debug_info["sample_activities"] = f"Error: {str(sample_error)}"

    except Exception as e:
        debug_info["database_connection"] = f"Error: {str(e)}"

    finally:
        if fresh_db:
            try:
                fresh_db.close()
            except:
                pass

    return f"""
    <html>
    <head><title>Activities Debug</title></head>
    <body>
        <h1>Activities Debug Information</h1>
        <pre>{debug_info}</pre>
        <a href="/admin/activities">Back to Activities</a>
    </body>
    </html>
    """

@router.get("/activities", response_class=HTMLResponse)
async def view_activities(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    activity_type: Optional[str] = None,
    user_search: Optional[str] = None,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """View system activities with pagination and filtering"""
    # Import ActivityType at the top to avoid UnboundLocalError
    from app.models.activity import Activity, ActivityType

    # Create multiple safe database sessions for different operations
    fresh_db = None

    try:
        fresh_db = create_safe_db_session()

        # Validate page and per_page parameters
        page = max(1, page)
        per_page = min(max(10, per_page), 100)  # Between 10 and 100

        # Calculate offset
        offset = (page - 1) * per_page

        # Check if activities table exists and has data
        try:
            # Use a simple count query to check table existence
            activities_count = fresh_db.query(Activity).count()
            logger.info(f"Activities table check passed. Total activities: {activities_count}")

            # Skip orphaned activities check for now to avoid transaction issues
            logger.info("Skipping orphaned activities check to avoid transaction issues")

        except Exception as table_error:
            logger.error(f"Activities table check failed: {table_error}")
            # Rollback the failed transaction
            fresh_db.rollback()
            # Create the table if it doesn't exist
            from app.database import Base, engine
            Base.metadata.create_all(bind=engine)
            logger.info("Created missing database tables")

        # Get real activities from database with minimal approach
        try:
            # Simple query without any user-related operations
            query = fresh_db.query(Activity)

            # Filter by activity type only
            if activity_type and activity_type != 'all' and activity_type.strip():
                try:
                    clean_activity_type = activity_type.strip().lower()
                    activity_type_enum = None
                    for at in ActivityType:
                        if at.value.lower() == clean_activity_type:
                            activity_type_enum = at
                            break
                    if activity_type_enum:
                        query = query.filter(Activity.activity_type == activity_type_enum)
                except Exception as type_error:
                    logger.warning(f"Error filtering by activity type: {type_error}")

            # Get total count first
            total_activities = query.count()

            # Apply pagination and get activities
            activities = query.order_by(Activity.created_at.desc()).offset(offset).limit(per_page).all()

        except Exception as query_error:
            logger.error(f"Error querying activities: {query_error}")
            activities = []
            total_activities = 0

        # If no activities exist, create some sample activities for testing
        if total_activities == 0 and not activity_type and not user_search:
            logger.info("No activities found, creating sample activities...")
            try:
                # datetime and timezone already imported as dt and timezone above

                # Create sample activities with a default user_id (assuming user 1 exists)
                # If user 1 doesn't exist, this will be handled gracefully
                sample_activities = [
                    Activity(
                        user_id=1,  # Use a default user ID
                        activity_type=ActivityType.LOGIN,
                        description="تسجيل دخول المستخدم",
                        created_at=dt.now(timezone.utc)
                    ),
                    Activity(
                        user_id=1,  # Use a default user ID
                        activity_type=ActivityType.PROFILE_UPDATED,
                        description="تحديث الملف الشخصي",
                        created_at=dt.now(timezone.utc)
                    )
                ]

                for activity in sample_activities:
                    fresh_db.add(activity)

                try:
                    fresh_db.commit()
                    logger.info(f"Created {len(sample_activities)} sample activities")

                    # Refresh the activities and count
                    activities = ActivityService.get_real_activities(
                        db=fresh_db,
                        activity_type=activity_type,
                        user_search=user_search,
                        limit=per_page,
                        skip=offset
                    )
                    total_activities = ActivityService.get_total_activities_count(
                        db=fresh_db,
                        activity_type=activity_type,
                        user_search=user_search
                    )
                except Exception as commit_error:
                    logger.error(f"Error committing sample activities: {commit_error}")
                    fresh_db.rollback()
            except Exception as sample_error:
                logger.error(f"Error creating sample activities: {sample_error}")
                fresh_db.rollback()

        # Calculate pagination info
        total_pages = max(1, (total_activities + per_page - 1) // per_page) if total_activities > 0 else 1
        has_prev = page > 1
        has_next = page < total_pages

        # Get activity type counts for filter (simplified to avoid transaction issues)
        activity_type_counts = {}
        try:
            for activity_type_enum in ActivityType:
                count = fresh_db.query(Activity).filter(
                    Activity.activity_type == activity_type_enum
                ).count()
                activity_type_counts[activity_type_enum.value] = count
        except Exception as count_error:
            logger.warning(f"Error getting activity type counts: {count_error}")
            activity_type_counts = {}

        return templates.TemplateResponse(
            "admin/activities.html",
            {
                "request": request,
                "current_user": current_user,
                "activities": activities,
                "current_page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "total_activities": total_activities,
                "has_prev": has_prev,
                "has_next": has_next,
                "current_activity_type": activity_type,
                "current_user_search": user_search,
                "activity_types": [t.value for t in ActivityType],
                "activity_type_counts": activity_type_counts
            }
        )

    except Exception as e:
        logger.error(f"Error in view_activities: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Ensure transaction is rolled back
        try:
            fresh_db.rollback()
        except:
            pass

        # Return error page or empty results
        return templates.TemplateResponse(
            "admin/activities.html",
            {
                "request": request,
                "current_user": current_user,
                "activities": [],
                "current_page": 1,
                "per_page": per_page,
                "total_pages": 1,
                "total_activities": 0,
                "has_prev": False,
                "has_next": False,
                "current_activity_type": activity_type,
                "current_user_search": user_search,
                "activity_types": [t.value for t in ActivityType],
                "activity_type_counts": {},
                "error": f"حدث خطأ في تحميل الأنشطة: {str(e)}"
            }
        )

    finally:
        # Always close the fresh database session
        try:
            fresh_db.close()
        except:
            pass


@router.get("/stats/export")
async def export_stats_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_cookie)
):
    """Export admin stats data to Excel file"""
    try:
        # Get comprehensive stats data
        stats_data = AchievementService.get_admin_stats_dashboard_data(db)

        # Create Excel file in memory
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # KPI Metrics Sheet
            kpi_data = []
            for metric_name, metric_info in stats_data['kpi_cards'].items():
                kpi_data.append({
                    'المؤشر': metric_name.replace('_', ' ').title(),
                    'القيمة الحالية': metric_info['current'],
                    'نسبة التغيير (%)': metric_info['change_percent'],
                    'الاتجاه': 'صاعد' if metric_info['trend'] == 'up' else 'هابط'
                })

            kpi_df = pd.DataFrame(kpi_data)
            kpi_df.to_excel(writer, sheet_name='المؤشرات الرئيسية', index=False)

            # Monthly Growth Sheet
            monthly_data = []
            for month_info in stats_data['monthly_growth']:
                monthly_data.append({
                    'الشهر': month_info['month'],
                    'عدد الطلبات': month_info['count']
                })

            monthly_df = pd.DataFrame(monthly_data)
            monthly_df.to_excel(writer, sheet_name='النمو الشهري', index=False)

            # Status Distribution Sheet
            status_data = []
            for status, count in stats_data['status_distribution'].items():
                total_requests = sum(stats_data['status_distribution'].values())
                percentage = (count / total_requests * 100) if total_requests > 0 else 0
                status_data.append({
                    'حالة الطلب': status.replace('_', ' ').title(),
                    'العدد': count,
                    'النسبة المئوية': f"{percentage:.1f}%"
                })

            status_df = pd.DataFrame(status_data)
            status_df.to_excel(writer, sheet_name='توزيع الحالات', index=False)

            # Top Request Types Sheet
            request_types_data = []
            for req_type in stats_data['top_request_types']:
                request_types_data.append({
                    'نوع الطلب': req_type['name'],
                    'العدد': req_type['count'],
                    'معدل الإنجاز (%)': req_type['completion_rate'],
                    'الفئة': req_type['category']
                })

            req_types_df = pd.DataFrame(request_types_data)
            req_types_df.to_excel(writer, sheet_name='أنواع الطلبات الأكثر شيوعاً', index=False)

            # Recent Activities Sheet
            activities_data = []
            for activity in stats_data['recent_activities']:
                activities_data.append({
                    'العنوان': activity['title'],
                    'الوصف': activity['description'],
                    'الوقت': activity['time'].strftime('%Y-%m-%d %H:%M:%S') if activity['time'] else '',
                    'النوع': activity['type']
                })

            activities_df = pd.DataFrame(activities_data)
            activities_df.to_excel(writer, sheet_name='الأنشطة الحديثة', index=False)

            # Summary Sheet
            summary_data = [
                {'المؤشر': 'إجمالي المستخدمين', 'القيمة': stats_data['kpi_cards']['total_users']['current']},
                {'المؤشر': 'معدل الإنجاز (%)', 'القيمة': stats_data['kpi_cards']['completion_rate']['current']},
                {'المؤشر': 'معدل المشاركة (%)', 'القيمة': stats_data['kpi_cards']['engagement_rate']['current']},
                {'المؤشر': 'نقاط الكفاءة', 'القيمة': stats_data['kpi_cards']['efficiency_score']['current']},
                {'المؤشر': 'إجمالي الطلبات', 'القيمة': sum(stats_data['status_distribution'].values())},
                {'المؤشر': 'تاريخ التصدير', 'القيمة': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            ]

            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='ملخص عام', index=False)

        output.seek(0)

        # Generate filename with current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        filename = f"admin_stats_{current_date}.xlsx"

        # Return file as streaming response
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting data: {str(e)}")


@router.get("/file-upload-test", response_class=HTMLResponse)
async def file_upload_test_page(
    request: Request,
    current_user: User = Depends(require_admin_cookie)
):
    """File upload test page for admins"""
    return templates.TemplateResponse(
        "admin/file_upload_test.html",
        {
            "request": request,
            "current_user": current_user
        }
    )


@router.post("/test-upload")
async def test_file_upload(
    request: Request,
    file: UploadFile = FastAPIFile(None),
    files: List[UploadFile] = FastAPIFile(None),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Test endpoint for file upload functionality"""
    try:
        # Determine if single or multiple file upload
        upload_files = []

        if file and file.filename:
            upload_files = [file]
        elif files and any(f.filename for f in files):
            upload_files = [f for f in files if f.filename]

        if not upload_files:
            return JSONResponse(
                status_code=400,
                content={"error": "No files provided"}
            )

        # Validate files using enhanced validation
        validation_result = await FileHandler.validate_multiple_files(upload_files)

        if not validation_result["valid"]:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "File validation failed",
                    "details": validation_result["errors"],
                    "warnings": validation_result.get("warnings", [])
                }
            )

        # For testing purposes, we'll simulate successful upload without actually saving
        # In a real scenario, you would save to a test request or temporary location

        result = {
            "success": True,
            "message": f"Successfully validated {len(upload_files)} file(s)",
            "successful_uploads": len(upload_files),
            "total_files_processed": len(upload_files),
            "warnings": validation_result.get("warnings", []),
            "file_details": []
        }

        # Add file details
        for file_result in validation_result.get("file_results", []):
            if file_result["validation"]["valid"]:
                file_info = file_result["validation"]["file_info"]
                result["file_details"].append({
                    "filename": file_info["filename"],
                    "size": file_info["size"],
                    "type": file_info["extension"],
                    "mime_type": file_info["mime_type"]
                })

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Upload test failed: {str(e)}"}
        )


@router.post("/validate-files")
async def validate_files_endpoint(
    request: Request,
    files: List[UploadFile] = FastAPIFile(...),
    current_user: User = Depends(require_admin_cookie)
):
    """Endpoint for file validation testing"""
    try:
        if not files or not any(f.filename for f in files):
            return JSONResponse(
                status_code=400,
                content={"error": "No files provided"}
            )

        valid_files = [f for f in files if f.filename]
        validation_result = await FileHandler.validate_multiple_files(valid_files)

        return JSONResponse(content={
            "validation_result": validation_result,
            "summary": {
                "total_files": len(valid_files),
                "valid_files": len([r for r in validation_result.get("file_results", []) if r["validation"]["valid"]]),
                "invalid_files": len([r for r in validation_result.get("file_results", []) if not r["validation"]["valid"]]),
                "total_size": validation_result.get("total_size", 0),
                "has_duplicates": len(validation_result.get("duplicate_hashes", [])) > 0
            }
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Validation failed: {str(e)}"}
        )


@router.post("/seed-activities")
async def seed_activities(
    request: Request,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Seed some sample activities for testing"""
    try:
        # datetime and timedelta already imported as dt and timedelta above
        import random

        # Get all users
        users = db.query(User).all()
        if not users:
            return {"error": "No users found"}

        # Sample activities to create
        sample_activities = [
            ("login", "تسجيل دخول المستخدم"),
            ("logout", "تسجيل خروج المستخدم"),
            ("request_created", "إنشاء طلب جديد"),
            ("request_updated", "تحديث طلب موجود"),
            ("file_uploaded", "رفع ملف جديد"),
            ("profile_updated", "تحديث الملف الشخصي"),
            ("password_changed", "تغيير كلمة المرور"),
        ]

        # Sample IP addresses for testing
        sample_ips = [
            "192.168.1.100",
            "10.0.0.50",
            "172.16.0.25",
            "203.0.113.45",
            "198.51.100.78"
        ]

        # Sample user agents
        sample_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)",
            "Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0"
        ]

        activities_created = 0

        # Create 50 sample activities
        for i in range(50):
            user = random.choice(users)
            activity_type, description = random.choice(sample_activities)
            ip_address = random.choice(sample_ips)
            user_agent = random.choice(sample_user_agents)

            # Create activity with random timestamp in the last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)

            activity_time = dt.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

            # Create activity record
            new_activity = Activity(
                user_id=user.id,
                activity_type=ActivityType(activity_type),
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=activity_time
            )

            db.add(new_activity)
            activities_created += 1

        db.commit()

        return {
            "success": True,
            "message": f"تم إنشاء {activities_created} نشاط تجريبي بنجاح",
            "activities_created": activities_created
        }

    except Exception as e:
        logger.error(f"Error seeding activities: {e}")
        db.rollback()
        return {"error": f"خطأ في إنشاء الأنشطة التجريبية: {str(e)}"}


@router.delete("/clear-activities")
async def clear_activities(
    request: Request,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Clear all activities (for testing)"""
    try:
        count = db.query(Activity).count()
        db.query(Activity).delete()
        db.commit()

        return {
            "success": True,
            "message": f"تم حذف {count} نشاط",
            "deleted_count": count
        }

    except Exception as e:
        logger.error(f"Error clearing activities: {e}")
        db.rollback()
        return {"error": f"خطأ في حذف الأنشطة: {str(e)}"}


# Debug routes for testing
@router.get("/debug/dropdown-fix-test", response_class=HTMLResponse)
async def dropdown_fix_test(request: Request):
    """Debug page to test dropdown fix"""
    return templates.TemplateResponse(
        "debug/dropdown_fix_test.html",
        {
            "request": request,
            "cache_bust": "1.0.0"
        }
    )

@router.get("/debug/dropdown-overlap-test", response_class=HTMLResponse)
async def dropdown_overlap_test(request: Request):
    """Debug page to test dropdown overlap issues"""
    return templates.TemplateResponse(
        "debug/dropdown_overlap_test.html",
        {
            "request": request,
            "cache_bust": "1.0.0"
        }
    )

@router.get("/debug/dropdown-text-debug", response_class=HTMLResponse)
async def dropdown_text_debug(request: Request):
    """Debug page to analyze dropdown text visibility issues"""
    return templates.TemplateResponse(
        "debug/dropdown_text_debug.html",
        {
            "request": request,
            "cache_bust": "1.0.0"
        }
    )

@router.get("/debug/dropdown-deep-debug", response_class=HTMLResponse)
async def dropdown_deep_debug(request: Request):
    """Deep debug page to find exact cause of dropdown issues"""
    return templates.TemplateResponse(
        "debug/dropdown_deep_debug.html",
        {
            "request": request,
            "cache_bust": "1.0.0"
        }
    )

@router.get("/debug/dropdown-inspector", response_class=HTMLResponse)
async def dropdown_inspector(request: Request):
    """Advanced dropdown inspector to find exact CSS conflicts"""
    return templates.TemplateResponse(
        "debug/dropdown_inspector.html",
        {
            "request": request,
            "cache_bust": "1.0.0"
        }
    )

@router.get("/debug/dropdown-simple-test", response_class=HTMLResponse)
async def dropdown_simple_test(request: Request):
    """Simple dropdown test with multiple approaches"""
    return templates.TemplateResponse(
        "debug/dropdown_simple_test.html",
        {
            "request": request,
            "cache_bust": "1.0.0"
        }
    )


