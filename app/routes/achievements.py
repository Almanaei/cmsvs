from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.utils.auth import verify_token
from app.services.achievement_service import AchievementService
from app.services.user_service import UserService
from app.models.user import User, UserRole
from app.models.achievement import AchievementType, CompetitionStatus, Competition, CompetitionParticipant

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

    return user


async def require_admin_cookie(request: Request, db: Session = Depends(get_db)) -> User:
    """Require admin role using cookie authentication"""
    user = await get_current_user_cookie(request, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/achievements", response_class=HTMLResponse)
async def achievements_page(
    request: Request,
    period: str = Query("global", description="Leaderboard period"),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Main achievements and competition page"""
    # Initialize achievements if needed
    AchievementService.initialize_default_achievements(db)

    # Sync user progress with actual request data to ensure accuracy
    AchievementService._sync_user_progress_with_requests(db, current_user.id)

    # Get user's achievement data
    user_data = AchievementService.get_user_dashboard_data(db, current_user.id)

    # Get all users progress data for admin view
    all_users_progress = None
    if current_user.role.value == 'admin':
        all_users_progress = AchievementService.get_all_users_progress_data(db)
    
    # Get leaderboard data
    leaderboard_data = AchievementService.get_leaderboard_data(db, period, limit=20)
    
    # Get active competitions
    active_competitions = AchievementService.get_active_competitions(db, current_user.id)
    
    return templates.TemplateResponse(
        "achievements/achievements_main.html",
        {
            "request": request,
            "current_user": current_user,
            "user_data": user_data,
            "leaderboard_data": leaderboard_data,
            "active_competitions": active_competitions,
            "current_period": period,
            "all_users_progress": all_users_progress
        }
    )


@router.get("/achievements/leaderboard", response_class=JSONResponse)
async def get_leaderboard_api(
    period: str = Query("global"),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """API endpoint for leaderboard data"""
    leaderboard_data = AchievementService.get_leaderboard_data(db, period, limit)
    return {"leaderboard": leaderboard_data, "period": period}


@router.get("/achievements/user/{user_id}", response_class=JSONResponse)
async def get_user_achievements(
    user_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get detailed achievement data for a specific user"""
    # Check if user can view this data (self or admin)
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_data = AchievementService.get_user_dashboard_data(db, user_id)
    return user_data


@router.post("/achievements/update-progress")
async def update_achievement_progress(
    completed_requests: int = Form(1),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Update user's achievement progress (called when requests are completed)"""
    AchievementService.update_user_progress(db, current_user.id, completed_requests)
    return {"status": "success", "message": "Progress updated"}


@router.post("/achievements/sync-progress")
async def sync_achievement_progress(
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Manually sync achievement progress with actual request data"""
    try:
        AchievementService._sync_user_progress_with_requests(db, current_user.id)
        return {"status": "success", "message": "تم تحديث التقدم بنجاح مع بيانات الطلبات الفعلية"}
    except Exception as e:
        return {"status": "error", "message": f"خطأ في تحديث التقدم: {str(e)}"}


@router.get("/competitions", response_class=HTMLResponse)
async def competitions_page(
    request: Request,
    status: str = Query("active", description="Competition status filter"),
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Competitions page"""
    # Get competitions based on status
    if status == "active":
        competitions = db.query(Competition).filter(
            Competition.status == CompetitionStatus.ACTIVE
        ).order_by(Competition.end_date).all()
    elif status == "upcoming":
        competitions = db.query(Competition).filter(
            Competition.status == CompetitionStatus.UPCOMING
        ).order_by(Competition.start_date).all()
    elif status == "completed":
        competitions = db.query(Competition).filter(
            Competition.status == CompetitionStatus.COMPLETED
        ).order_by(desc(Competition.end_date)).limit(10).all()
    else:
        competitions = db.query(Competition).order_by(desc(Competition.created_at)).limit(20).all()
    
    # Get user's participation status for each competition
    competitions_data = []
    for comp in competitions:
        participant = db.query(CompetitionParticipant).filter(
            CompetitionParticipant.competition_id == comp.id,
            CompetitionParticipant.user_id == current_user.id
        ).first()
        
        total_participants = db.query(CompetitionParticipant).filter(
            CompetitionParticipant.competition_id == comp.id
        ).count()
        
        competitions_data.append({
            "competition": comp,
            "is_participating": participant is not None,
            "user_progress": participant.current_progress if participant else 0,
            "total_participants": total_participants
        })
    
    return templates.TemplateResponse(
        "achievements/competitions.html",
        {
            "request": request,
            "current_user": current_user,
            "competitions_data": competitions_data,
            "current_status": status
        }
    )


@router.post("/competitions/{competition_id}/join")
async def join_competition(
    competition_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Join a competition"""
    success = AchievementService.join_competition(db, competition_id, current_user.id)
    
    if success:
        return {"status": "success", "message": "تم الانضمام للمسابقة بنجاح!"}
    else:
        return {"status": "error", "message": "فشل في الانضمام للمسابقة"}


@router.get("/competitions/{competition_id}/leaderboard", response_class=JSONResponse)
async def get_competition_leaderboard(
    competition_id: int,
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get leaderboard for a specific competition"""
    leaderboard = AchievementService.get_competition_leaderboard(db, competition_id)
    return {"leaderboard": leaderboard}


@router.get("/admin/competitions/create", response_class=HTMLResponse)
async def create_competition_form(
    request: Request,
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Form to create new competition (admin only)"""
    return templates.TemplateResponse(
        "achievements/create_competition.html",
        {
            "request": request,
            "current_user": current_user
        }
    )


@router.post("/admin/competitions/create")
async def create_competition(
    name: str = Form(...),
    description: str = Form(...),
    competition_type: str = Form(...),
    target_value: int = Form(...),
    start_date: datetime = Form(...),
    end_date: datetime = Form(...),
    first_place_points: int = Form(100),
    second_place_points: int = Form(75),
    third_place_points: int = Form(50),
    participation_points: int = Form(10),
    max_participants: Optional[int] = Form(None),
    is_public: bool = Form(True),
    current_user: User = Depends(require_admin_cookie),
    db: Session = Depends(get_db)
):
    """Create new competition (admin only)"""
    try:
        competition_data = {
            "name": name,
            "description": description,
            "type": competition_type,
            "target": target_value,
            "start_date": start_date,
            "end_date": end_date,
            "first_place_points": first_place_points,
            "second_place_points": second_place_points,
            "third_place_points": third_place_points,
            "participation_points": participation_points,
            "max_participants": max_participants,
            "is_public": is_public
        }
        
        competition = AchievementService.create_competition(db, current_user.id, competition_data)
        
        return templates.TemplateResponse(
            "achievements/competition_created.html",
            {
                "request": request,
                "current_user": current_user,
                "competition": competition,
                "success": "تم إنشاء المسابقة بنجاح!"
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "achievements/create_competition.html",
            {
                "request": request,
                "current_user": current_user,
                "error": f"خطأ في إنشاء المسابقة: {str(e)}"
            }
        )


@router.get("/achievements/stats", response_class=JSONResponse)
async def get_achievement_stats(
    current_user: User = Depends(get_current_user_cookie),
    db: Session = Depends(get_db)
):
    """Get achievement statistics for dashboard widgets"""
    user_data = AchievementService.get_user_dashboard_data(db, current_user.id)

    return {
        "daily_progress": user_data["current_progress"]["daily"],
        "weekly_progress": user_data["current_progress"]["weekly"],
        "monthly_progress": user_data["current_progress"]["monthly"],
        "user_stats": user_data["user_stats"],
        "recent_achievements": user_data["recent_achievements"][:3]  # Only latest 3
    }



