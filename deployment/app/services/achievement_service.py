from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta, date
import calendar
from app.models.achievement import (
    Achievement, UserAchievement, Competition, CompetitionParticipant, 
    UserStats, AchievementType, CompetitionStatus
)
from app.models.user import User, UserRole
from app.models.request import Request, RequestStatus
import threading


class AchievementService:
    """Service for managing achievements and competitions"""
    
    # Thread-safe lock for achievement updates
    _achievement_lock = threading.Lock()
    
    @staticmethod
    def initialize_default_achievements(db: Session):
        """Initialize default achievement templates"""
        default_achievements = [
            # Daily Achievements
            {
                "name": "إنجاز يومي",
                "description": "أكمل 10 طلبات في يوم واحد",
                "achievement_type": AchievementType.DAILY,
                "target_value": 10,
                "points": 50,
                "badge_icon": "🌟",
                "badge_color": "yellow"
            },
            {
                "name": "نشاط يومي",
                "description": "أكمل 5 طلبات في يوم واحد",
                "achievement_type": AchievementType.DAILY,
                "target_value": 5,
                "points": 25,
                "badge_icon": "⭐",
                "badge_color": "blue"
            },
            
            # Weekly Achievements
            {
                "name": "إنجاز أسبوعي",
                "description": "أكمل 50 طلب في أسبوع واحد",
                "achievement_type": AchievementType.WEEKLY,
                "target_value": 50,
                "points": 200,
                "badge_icon": "🏆",
                "badge_color": "gold"
            },
            {
                "name": "نشاط أسبوعي",
                "description": "أكمل 25 طلب في أسبوع واحد",
                "achievement_type": AchievementType.WEEKLY,
                "target_value": 25,
                "points": 100,
                "badge_icon": "🥇",
                "badge_color": "silver"
            },
            
            # Monthly Achievements
            {
                "name": "إنجاز شهري",
                "description": "أكمل 200 طلب في شهر واحد",
                "achievement_type": AchievementType.MONTHLY,
                "target_value": 200,
                "points": 500,
                "badge_icon": "👑",
                "badge_color": "purple"
            },
            {
                "name": "نشاط شهري",
                "description": "أكمل 100 طلب في شهر واحد",
                "achievement_type": AchievementType.MONTHLY,
                "target_value": 100,
                "points": 250,
                "badge_icon": "💎",
                "badge_color": "green"
            },
            
            # Milestone Achievements
            {
                "name": "المبتدئ",
                "description": "أكمل أول 10 طلبات",
                "achievement_type": AchievementType.MILESTONE,
                "target_value": 10,
                "points": 100,
                "badge_icon": "🎯",
                "badge_color": "green"
            },
            {
                "name": "المحترف",
                "description": "أكمل 100 طلب إجمالي",
                "achievement_type": AchievementType.MILESTONE,
                "target_value": 100,
                "points": 300,
                "badge_icon": "🚀",
                "badge_color": "blue"
            },
            {
                "name": "الخبير",
                "description": "أكمل 500 طلب إجمالي",
                "achievement_type": AchievementType.MILESTONE,
                "target_value": 500,
                "points": 1000,
                "badge_icon": "🌟",
                "badge_color": "gold"
            },
            
            # Streak Achievements
            {
                "name": "متسق",
                "description": "حقق الهدف اليومي لمدة 7 أيام متتالية",
                "achievement_type": AchievementType.STREAK,
                "target_value": 7,
                "points": 300,
                "badge_icon": "🔥",
                "badge_color": "red"
            },
            {
                "name": "مثابر",
                "description": "حقق الهدف اليومي لمدة 30 يوم متتالي",
                "achievement_type": AchievementType.STREAK,
                "target_value": 30,
                "points": 1000,
                "badge_icon": "💪",
                "badge_color": "orange"
            }
        ]
        
        for achievement_data in default_achievements:
            # Check if achievement already exists
            existing = db.query(Achievement).filter(
                Achievement.name == achievement_data["name"]
            ).first()
            
            if not existing:
                achievement = Achievement(**achievement_data)
                db.add(achievement)
        
        db.commit()
    
    @staticmethod
    def update_user_progress(db: Session, user_id: int, completed_requests: int = 1):
        """Update user progress for all applicable achievements"""
        with AchievementService._achievement_lock:
            now = datetime.utcnow()
            today = now.date()
            
            # Get or create user stats
            user_stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
            if not user_stats:
                user_stats = UserStats(user_id=user_id)
                db.add(user_stats)
                db.commit()
                db.refresh(user_stats)
            
            # Update daily achievements
            AchievementService._update_daily_achievements(db, user_id, today, completed_requests)
            
            # Update weekly achievements
            AchievementService._update_weekly_achievements(db, user_id, now, completed_requests)
            
            # Update monthly achievements
            AchievementService._update_monthly_achievements(db, user_id, now, completed_requests)
            
            # Update milestone achievements
            AchievementService._update_milestone_achievements(db, user_id)
            
            # Update streak achievements
            AchievementService._update_streak_achievements(db, user_id, user_stats)
            
            # Update user stats
            AchievementService._update_user_stats(db, user_id, user_stats)
            
            # Update competition progress
            AchievementService._update_competition_progress(db, user_id, completed_requests)
            
            db.commit()

    @staticmethod
    def _sync_user_progress_with_requests(db: Session, user_id: int):
        """Sync achievement progress with actual request completion data"""
        now = datetime.utcnow()
        today = now.date()

        # Get actual request completion counts
        daily_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            func.date(Request.updated_at) == today
        ).count()

        # Get weekly completed (current week)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        weekly_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.updated_at >= week_start
        ).count()

        # Get monthly completed (current month)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.updated_at >= month_start
        ).count()

        # Update daily achievements with actual data
        daily_achievements = db.query(UserAchievement).join(Achievement).filter(
            UserAchievement.user_id == user_id,
            Achievement.achievement_type == AchievementType.DAILY,
            func.date(UserAchievement.period_start) == today
        ).all()

        for ua in daily_achievements:
            if ua.current_progress != daily_completed:
                ua.current_progress = daily_completed
                # Check if achievement should be completed
                if daily_completed >= ua.achievement.target_value and not ua.is_completed:
                    ua.is_completed = True
                    ua.completed_at = now
                    ua.points_earned = ua.achievement.points

        # Update weekly achievements with actual data
        weekly_achievements = db.query(UserAchievement).join(Achievement).filter(
            UserAchievement.user_id == user_id,
            Achievement.achievement_type == AchievementType.WEEKLY,
            UserAchievement.period_start == week_start
        ).all()

        for ua in weekly_achievements:
            if ua.current_progress != weekly_completed:
                ua.current_progress = weekly_completed
                # Check if achievement should be completed
                if weekly_completed >= ua.achievement.target_value and not ua.is_completed:
                    ua.is_completed = True
                    ua.completed_at = now
                    ua.points_earned = ua.achievement.points

        # Update monthly achievements with actual data
        monthly_achievements = db.query(UserAchievement).join(Achievement).filter(
            UserAchievement.user_id == user_id,
            Achievement.achievement_type == AchievementType.MONTHLY,
            UserAchievement.period_start == month_start
        ).all()

        for ua in monthly_achievements:
            if ua.current_progress != monthly_completed:
                ua.current_progress = monthly_completed
                # Check if achievement should be completed
                if monthly_completed >= ua.achievement.target_value and not ua.is_completed:
                    ua.is_completed = True
                    ua.completed_at = now
                    ua.points_earned = ua.achievement.points

        db.commit()

    @staticmethod
    def _get_user_performance_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """Calculate comprehensive and intuitive performance statistics for a user"""
        now = datetime.utcnow()
        today = now.date()

        # Total requests and completion rate
        total_requests = db.query(Request).filter(Request.user_id == user_id).count()
        completed_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED
        ).count()

        pending_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.PENDING
        ).count()

        in_progress_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.IN_PROGRESS
        ).count()

        completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0

        # Today's performance
        today_total = db.query(Request).filter(
            Request.user_id == user_id,
            func.date(Request.created_at) == today
        ).count()

        today_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            func.date(Request.updated_at) == today
        ).count()

        today_target = 10
        today_progress = min(100, (today_completed / today_target * 100)) if today_target > 0 else 0

        # Calculate today's performance level
        if today_completed >= today_target:
            today_level = {"text": "ممتاز", "color": "#10B981", "icon": "🏆"}
        elif today_completed >= today_target * 0.8:
            today_level = {"text": "جيد جداً", "color": "#3B82F6", "icon": "⭐"}
        elif today_completed >= today_target * 0.6:
            today_level = {"text": "جيد", "color": "#F59E0B", "icon": "👍"}
        elif today_completed >= today_target * 0.3:
            today_level = {"text": "مقبول", "color": "#EF4444", "icon": "📈"}
        else:
            today_level = {"text": "يحتاج تحسين", "color": "#8B5CF6", "icon": "🎯"}

        # This week's performance
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        week_total = db.query(Request).filter(
            Request.user_id == user_id,
            Request.created_at >= week_start
        ).count()

        week_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.updated_at >= week_start
        ).count()

        week_target = 50
        week_progress = min(100, (week_completed / week_target * 100)) if week_target > 0 else 0

        # Calculate week's performance level
        if week_completed >= week_target:
            week_level = {"text": "ممتاز", "color": "#10B981", "icon": "🏆"}
        elif week_completed >= week_target * 0.8:
            week_level = {"text": "جيد جداً", "color": "#3B82F6", "icon": "⭐"}
        elif week_completed >= week_target * 0.6:
            week_level = {"text": "جيد", "color": "#F59E0B", "icon": "👍"}
        elif week_completed >= week_target * 0.3:
            week_level = {"text": "مقبول", "color": "#EF4444", "icon": "📈"}
        else:
            week_level = {"text": "يحتاج تحسين", "color": "#8B5CF6", "icon": "🎯"}

        # This month's performance
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        month_total = db.query(Request).filter(
            Request.user_id == user_id,
            Request.created_at >= month_start
        ).count()

        month_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.updated_at >= month_start
        ).count()

        month_target = 200
        month_progress = min(100, (month_completed / month_target * 100)) if month_target > 0 else 0

        # Calculate month's performance level
        if month_completed >= month_target:
            month_level = {"text": "ممتاز", "color": "#10B981", "icon": "🏆"}
        elif month_completed >= month_target * 0.8:
            month_level = {"text": "جيد جداً", "color": "#3B82F6", "icon": "⭐"}
        elif month_completed >= month_target * 0.6:
            month_level = {"text": "جيد", "color": "#F59E0B", "icon": "👍"}
        elif month_completed >= month_target * 0.3:
            month_level = {"text": "مقبول", "color": "#EF4444", "icon": "📈"}
        else:
            month_level = {"text": "يحتاج تحسين", "color": "#8B5CF6", "icon": "🎯"}

        # Average completion time (in days)
        completed_requests_with_times = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.updated_at.isnot(None)
        ).all()

        avg_completion_days = 0
        if completed_requests_with_times:
            total_days = sum([
                (req.updated_at - req.created_at).days
                for req in completed_requests_with_times
            ])
            avg_completion_days = total_days / len(completed_requests_with_times)

        # Calculate productivity metrics
        user = db.query(User).filter(User.id == user_id).first()
        days_since_registration = (now.date() - user.created_at.date()).days if user else 1
        daily_average = completed_requests / max(days_since_registration, 1)

        # Calculate efficiency score (0-100)
        efficiency_factors = [
            min(100, completion_rate),  # Completion rate weight: 40%
            min(100, (daily_average / 5) * 100),  # Daily average weight: 30% (5 requests/day = 100%)
            min(100, max(0, 100 - (avg_completion_days * 10))),  # Speed weight: 30% (1 day = 90%, 2 days = 80%, etc.)
        ]
        efficiency_score = (efficiency_factors[0] * 0.4 + efficiency_factors[1] * 0.3 + efficiency_factors[2] * 0.3)

        return {
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "pending_requests": pending_requests,
            "in_progress_requests": in_progress_requests,
            "completion_rate": round(completion_rate, 1),
            "avg_completion_days": round(avg_completion_days, 1),
            "daily_average": round(daily_average, 1),
            "efficiency_score": round(efficiency_score, 1),
            "days_since_registration": days_since_registration,
            "today": {
                "total": today_total,
                "completed": today_completed,
                "target": today_target,
                "progress_percentage": round(today_progress, 1),
                "remaining": max(0, today_target - today_completed),
                "level": today_level,
                "status": AchievementService._get_progress_status(today_progress)
            },
            "week": {
                "total": week_total,
                "completed": week_completed,
                "target": week_target,
                "progress_percentage": round(week_progress, 1),
                "remaining": max(0, week_target - week_completed),
                "level": week_level,
                "status": AchievementService._get_progress_status(week_progress),
                "days_left": 7 - today.weekday()
            },
            "month": {
                "total": month_total,
                "completed": month_completed,
                "target": month_target,
                "progress_percentage": round(month_progress, 1),
                "remaining": max(0, month_target - month_completed),
                "level": month_level,
                "status": AchievementService._get_progress_status(month_progress),
                "days_left": AchievementService._calculate_days_left_in_month(today)
            }
        }

    @staticmethod
    def _get_progress_status(progress_percentage: float) -> Dict[str, str]:
        """Get intuitive progress status based on percentage"""
        if progress_percentage >= 100:
            return {"text": "مكتمل", "color": "#10B981", "icon": "✅"}
        elif progress_percentage >= 90:
            return {"text": "قريب جداً", "color": "#059669", "icon": "🔥"}
        elif progress_percentage >= 75:
            return {"text": "تقدم ممتاز", "color": "#3B82F6", "icon": "⚡"}
        elif progress_percentage >= 50:
            return {"text": "في المسار الصحيح", "color": "#F59E0B", "icon": "📈"}
        elif progress_percentage >= 25:
            return {"text": "بداية جيدة", "color": "#EF4444", "icon": "🚀"}
        else:
            return {"text": "ابدأ الآن", "color": "#8B5CF6", "icon": "🎯"}

    @staticmethod
    def _calculate_days_left_in_month(today: date) -> int:
        """Calculate days left in the current month"""
        try:
            # Get the last day of current month
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)

            # Calculate days left
            days_left = (next_month - today).days
            return max(0, days_left)
        except Exception:
            # Fallback calculation
            import calendar
            last_day = calendar.monthrange(today.year, today.month)[1]
            return max(0, last_day - today.day)

    @staticmethod
    def _update_daily_achievements(db: Session, user_id: int, today: date, completed_requests: int):
        """Update daily achievement progress"""
        daily_achievements = db.query(Achievement).filter(
            Achievement.achievement_type == AchievementType.DAILY,
            Achievement.is_active == True
        ).all()
        
        for achievement in daily_achievements:
            # Get or create user achievement for today
            user_achievement = db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id,
                func.date(UserAchievement.period_start) == today
            ).first()
            
            if not user_achievement:
                # Create new daily achievement tracking
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    period_start=datetime.combine(today, datetime.min.time()),
                    period_end=datetime.combine(today, datetime.max.time()),
                    current_progress=0
                )
                db.add(user_achievement)
            
            # Update progress
            user_achievement.current_progress += completed_requests
            
            # Check if achievement is completed
            if (user_achievement.current_progress >= achievement.target_value and 
                not user_achievement.is_completed):
                user_achievement.is_completed = True
                user_achievement.completed_at = datetime.utcnow()
                user_achievement.points_earned = achievement.points
    
    @staticmethod
    def _update_weekly_achievements(db: Session, user_id: int, now: datetime, completed_requests: int):
        """Update weekly achievement progress"""
        # Get start of current week (Monday)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        weekly_achievements = db.query(Achievement).filter(
            Achievement.achievement_type == AchievementType.WEEKLY,
            Achievement.is_active == True
        ).all()
        
        for achievement in weekly_achievements:
            # Get or create user achievement for this week
            user_achievement = db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id,
                UserAchievement.period_start == week_start
            ).first()
            
            if not user_achievement:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    period_start=week_start,
                    period_end=week_end,
                    current_progress=0
                )
                db.add(user_achievement)
            
            # Update progress
            user_achievement.current_progress += completed_requests
            
            # Check if achievement is completed
            if (user_achievement.current_progress >= achievement.target_value and 
                not user_achievement.is_completed):
                user_achievement.is_completed = True
                user_achievement.completed_at = datetime.utcnow()
                user_achievement.points_earned = achievement.points
    
    @staticmethod
    def _update_monthly_achievements(db: Session, user_id: int, now: datetime, completed_requests: int):
        """Update monthly achievement progress"""
        # Get start of current month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Get end of current month
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(seconds=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(seconds=1)
        
        monthly_achievements = db.query(Achievement).filter(
            Achievement.achievement_type == AchievementType.MONTHLY,
            Achievement.is_active == True
        ).all()
        
        for achievement in monthly_achievements:
            # Get or create user achievement for this month
            user_achievement = db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id,
                UserAchievement.period_start == month_start
            ).first()
            
            if not user_achievement:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    period_start=month_start,
                    period_end=month_end,
                    current_progress=0
                )
                db.add(user_achievement)
            
            # Update progress
            user_achievement.current_progress += completed_requests
            
            # Check if achievement is completed
            if (user_achievement.current_progress >= achievement.target_value and
                not user_achievement.is_completed):
                user_achievement.is_completed = True
                user_achievement.completed_at = datetime.utcnow()
                user_achievement.points_earned = achievement.points

    @staticmethod
    def _update_milestone_achievements(db: Session, user_id: int):
        """Update milestone achievement progress"""
        # Get total completed requests for user
        total_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED
        ).count()

        milestone_achievements = db.query(Achievement).filter(
            Achievement.achievement_type == AchievementType.MILESTONE,
            Achievement.is_active == True
        ).all()

        for achievement in milestone_achievements:
            # Check if user already has this achievement
            user_achievement = db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            ).first()

            if not user_achievement:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    current_progress=total_completed
                )
                db.add(user_achievement)
            else:
                user_achievement.current_progress = total_completed

            # Check if achievement is completed
            if (user_achievement.current_progress >= achievement.target_value and
                not user_achievement.is_completed):
                user_achievement.is_completed = True
                user_achievement.completed_at = datetime.utcnow()
                user_achievement.points_earned = achievement.points

    @staticmethod
    def _update_streak_achievements(db: Session, user_id: int, user_stats: UserStats):
        """Update streak achievement progress"""
        streak_achievements = db.query(Achievement).filter(
            Achievement.achievement_type == AchievementType.STREAK,
            Achievement.is_active == True
        ).all()

        for achievement in streak_achievements:
            # Check current streak against achievement target
            current_streak = user_stats.current_daily_streak

            # Check if user already has this achievement
            user_achievement = db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            ).first()

            if not user_achievement:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    current_progress=current_streak
                )
                db.add(user_achievement)
            else:
                user_achievement.current_progress = current_streak

            # Check if achievement is completed
            if (user_achievement.current_progress >= achievement.target_value and
                not user_achievement.is_completed):
                user_achievement.is_completed = True
                user_achievement.completed_at = datetime.utcnow()
                user_achievement.points_earned = achievement.points

    @staticmethod
    def _update_user_stats(db: Session, user_id: int, user_stats: UserStats):
        """Update user statistics"""
        now = datetime.utcnow()
        today = now.date()

        # Calculate daily streak
        if user_stats.last_daily_completion:
            last_completion_date = user_stats.last_daily_completion.date()
            if last_completion_date == today:
                # Already completed today, no change to streak
                pass
            elif last_completion_date == today - timedelta(days=1):
                # Completed yesterday, continue streak
                user_stats.current_daily_streak += 1
                user_stats.last_daily_completion = now
            else:
                # Gap in completion, reset streak
                user_stats.current_daily_streak = 1
                user_stats.last_daily_completion = now
        else:
            # First completion
            user_stats.current_daily_streak = 1
            user_stats.last_daily_completion = now

        # Update longest streak
        if user_stats.current_daily_streak > user_stats.longest_daily_streak:
            user_stats.longest_daily_streak = user_stats.current_daily_streak

        # Calculate total points from completed achievements
        total_points = db.query(func.sum(UserAchievement.points_earned)).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.is_completed == True
        ).scalar() or 0

        user_stats.total_points = total_points

        # Update achievement counts
        user_stats.total_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.is_completed == True
        ).count()

    @staticmethod
    def _update_competition_progress(db: Session, user_id: int, completed_requests: int):
        """Update progress in active competitions"""
        # Get active competitions
        active_competitions = db.query(Competition).filter(
            Competition.status == CompetitionStatus.ACTIVE,
            Competition.start_date <= datetime.utcnow(),
            Competition.end_date >= datetime.utcnow()
        ).all()

        for competition in active_competitions:
            # Check if user is participating
            participant = db.query(CompetitionParticipant).filter(
                CompetitionParticipant.competition_id == competition.id,
                CompetitionParticipant.user_id == user_id
            ).first()

            if participant:
                participant.current_progress += completed_requests
                participant.last_updated = datetime.utcnow()

    @staticmethod
    def get_all_users_progress_data(db: Session) -> List[Dict[str, Any]]:
        """Get comprehensive progress data for all users for admin charts"""
        now = datetime.utcnow()
        today = now.date()

        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        users_progress = []

        for user in users:
            # Get user stats
            user_stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()
            if not user_stats:
                user_stats = UserStats(user_id=user.id)
                db.add(user_stats)
                db.commit()
                db.refresh(user_stats)

            # Get performance statistics
            performance_stats = AchievementService._get_user_performance_stats(db, user.id)

            # Get current period progress
            daily_progress = AchievementService._get_daily_progress(db, user.id, today)
            weekly_progress = AchievementService._get_weekly_progress(db, user.id, now)
            monthly_progress = AchievementService._get_monthly_progress(db, user.id, now)

            # Get recent achievements count
            recent_achievements_count = db.query(UserAchievement).filter(
                UserAchievement.user_id == user.id,
                UserAchievement.is_completed == True,
                UserAchievement.completed_at >= now - timedelta(days=30)
            ).count()

            # Calculate overall performance score
            daily_score = (daily_progress["achievements"][0]["current_progress"] / daily_progress["achievements"][0]["target_value"] * 100) if daily_progress["achievements"] else 0
            weekly_score = (weekly_progress["achievements"][0]["current_progress"] / weekly_progress["achievements"][0]["target_value"] * 100) if weekly_progress["achievements"] else 0
            monthly_score = (monthly_progress["achievements"][0]["current_progress"] / monthly_progress["achievements"][0]["target_value"] * 100) if monthly_progress["achievements"] else 0

            overall_score = (daily_score + weekly_score + monthly_score) / 3

            # Determine performance level
            if overall_score >= 80:
                performance_level = "ممتاز"
                performance_color = "#10B981"  # Green
                performance_icon = "🏆"
            elif overall_score >= 60:
                performance_level = "جيد جداً"
                performance_color = "#3B82F6"  # Blue
                performance_icon = "🥈"
            elif overall_score >= 40:
                performance_level = "جيد"
                performance_color = "#F59E0B"  # Yellow
                performance_icon = "🥉"
            elif overall_score >= 20:
                performance_level = "مقبول"
                performance_color = "#EF4444"  # Red
                performance_icon = "📈"
            else:
                performance_level = "يحتاج تحسين"
                performance_color = "#6B7280"  # Gray
                performance_icon = "📊"

            users_progress.append({
                "user_id": user.id,
                "user_info": {
                    "full_name": user.full_name,
                    "username": user.username,
                    "role": user.role.value,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                },
                "stats": {
                    "total_points": user_stats.total_points,
                    "current_streak": user_stats.current_daily_streak,
                    "longest_streak": user_stats.longest_daily_streak,
                    "total_achievements": user_stats.total_achievements,
                    "global_rank": user_stats.global_rank or len(users)
                },
                "performance": {
                    "daily_completed": performance_stats["today"]["completed"],
                    "weekly_completed": performance_stats["week"]["completed"],
                    "monthly_completed": performance_stats["month"]["completed"],
                    "completion_rate": performance_stats["completion_rate"],
                    "avg_completion_days": performance_stats["avg_completion_days"],
                    "total_requests": performance_stats["total_requests"],
                    "completed_requests": performance_stats["completed_requests"]
                },
                "progress_scores": {
                    "daily": min(daily_score, 100),
                    "weekly": min(weekly_score, 100),
                    "monthly": min(monthly_score, 100),
                    "overall": min(overall_score, 100)
                },
                "performance_level": {
                    "text": performance_level,
                    "color": performance_color,
                    "icon": performance_icon
                },
                "recent_achievements_count": recent_achievements_count
            })

        # Sort by overall performance score
        users_progress.sort(key=lambda x: x["progress_scores"]["overall"], reverse=True)

        return users_progress

    @staticmethod
    def get_admin_stats_dashboard_data(db: Session) -> dict:
        """Get comprehensive statistics for admin stats dashboard"""
        from app.models.request import Request as RequestModel
        from app.models.user import User, UserRole
        from app.models.activity import Activity
        from datetime import datetime, timedelta
        from sqlalchemy import func, extract

        # Get current date and calculate periods
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        # Total Users (equivalent to subscribers)
        total_users = db.query(User).filter(User.role == UserRole.USER).count()
        total_users_30_days_ago = db.query(User).filter(
            User.role == UserRole.USER,
            User.created_at <= thirty_days_ago
        ).count()

        # Request completion rate (equivalent to open rate)
        total_requests = db.query(RequestModel).count()
        completed_requests = db.query(RequestModel).filter(RequestModel.status == 'COMPLETED').count()
        completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0

        # Previous period completion rate
        total_requests_30_days_ago = db.query(RequestModel).filter(
            RequestModel.created_at <= thirty_days_ago
        ).count()
        completed_requests_30_days_ago = db.query(RequestModel).filter(
            RequestModel.status == 'COMPLETED',
            RequestModel.created_at <= thirty_days_ago
        ).count()
        completion_rate_30_days_ago = (completed_requests_30_days_ago / total_requests_30_days_ago * 100) if total_requests_30_days_ago > 0 else 0

        # User engagement rate (equivalent to click rate)
        active_users_30_days = db.query(User).filter(
            User.role == UserRole.USER,
            User.updated_at >= thirty_days_ago
        ).count()
        engagement_rate = (active_users_30_days / total_users * 100) if total_users > 0 else 0

        # Previous engagement rate
        active_users_60_to_30_days = db.query(User).filter(
            User.role == UserRole.USER,
            User.updated_at >= (thirty_days_ago - timedelta(days=30)),
            User.updated_at < thirty_days_ago
        ).count()
        total_users_60_days_ago = db.query(User).filter(
            User.role == UserRole.USER,
            User.created_at <= (thirty_days_ago - timedelta(days=30))
        ).count()
        engagement_rate_prev = (active_users_60_to_30_days / total_users_60_days_ago * 100) if total_users_60_days_ago > 0 else 0

        # System efficiency score (equivalent to revenue)
        pending_requests = db.query(RequestModel).filter(RequestModel.status == 'PENDING').count()
        in_progress_requests = db.query(RequestModel).filter(RequestModel.status == 'IN_PROGRESS').count()
        efficiency_score = max(0, 100 - (pending_requests + in_progress_requests) / total_requests * 100) if total_requests > 0 else 100

        # Previous efficiency score
        pending_requests_30_days_ago = db.query(RequestModel).filter(
            RequestModel.status == 'PENDING',
            RequestModel.created_at <= thirty_days_ago
        ).count()
        in_progress_requests_30_days_ago = db.query(RequestModel).filter(
            RequestModel.status == 'IN_PROGRESS',
            RequestModel.created_at <= thirty_days_ago
        ).count()
        efficiency_score_prev = max(0, 100 - (pending_requests_30_days_ago + in_progress_requests_30_days_ago) / total_requests_30_days_ago * 100) if total_requests_30_days_ago > 0 else 100

        # Monthly requests growth data for chart
        monthly_growth = []
        for i in range(7):
            month_start = now.replace(day=1) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            requests_count = db.query(RequestModel).filter(
                RequestModel.created_at <= month_end
            ).count()

            monthly_growth.insert(0, {
                'month': month_start.strftime('%b'),
                'count': requests_count
            })

        # Request status distribution for doughnut chart
        status_distribution = {
            'completed': completed_requests,
            'pending': pending_requests,
            'in_progress': in_progress_requests,
            'rejected': db.query(RequestModel).filter(RequestModel.status == 'REJECTED').count()
        }

        # Top performing request types
        top_request_types = db.query(
            RequestModel.request_name,
            func.count(RequestModel.id).label('count')
        ).group_by(RequestModel.request_name).order_by(func.count(RequestModel.id).desc()).limit(3).all()

        # Recent activities
        recent_activities = db.query(Activity).order_by(Activity.created_at.desc()).limit(3).all()

        return {
            'kpi_cards': {
                'total_users': {
                    'current': total_users,
                    'previous': total_users_30_days_ago,
                    'change_percent': round(((total_users - total_users_30_days_ago) / total_users_30_days_ago * 100), 2) if total_users_30_days_ago > 0 else 0,
                    'trend': 'up' if total_users > total_users_30_days_ago else 'down'
                },
                'completion_rate': {
                    'current': round(completion_rate, 2),
                    'previous': round(completion_rate_30_days_ago, 2),
                    'change_percent': round(completion_rate - completion_rate_30_days_ago, 2),
                    'trend': 'up' if completion_rate > completion_rate_30_days_ago else 'down'
                },
                'engagement_rate': {
                    'current': round(engagement_rate, 2),
                    'previous': round(engagement_rate_prev, 2),
                    'change_percent': round(engagement_rate - engagement_rate_prev, 2),
                    'trend': 'up' if engagement_rate > engagement_rate_prev else 'down'
                },
                'efficiency_score': {
                    'current': round(efficiency_score, 2),
                    'previous': round(efficiency_score_prev, 2),
                    'change_percent': round(efficiency_score - efficiency_score_prev, 2),
                    'trend': 'up' if efficiency_score > efficiency_score_prev else 'down'
                }
            },
            'monthly_growth': monthly_growth,
            'status_distribution': status_distribution,
            'top_request_types': [
                {
                    'name': req_type.request_name or 'غير محدد',
                    'count': req_type.count,
                    'completion_rate': round((completed_requests / total_requests * 100) if total_requests > 0 else 0, 1),
                    'category': 'طلب خدمة'
                }
                for req_type in top_request_types
            ],
            'recent_activities': [
                {
                    'title': activity.activity_type.value if activity.activity_type else 'نشاط',
                    'description': activity.description or f"تم تنفيذ {activity.activity_type.value if activity.activity_type else 'نشاط'}",
                    'time': activity.created_at,
                    'type': activity.activity_type.value if activity.activity_type else 'info'
                }
                for activity in recent_activities
            ]
        }

    @staticmethod
    def get_admin_leaderboard_data(db: Session) -> Dict[str, Any]:
        """Get top users leaderboard data for administrator dashboard"""
        from app.models.user import User, UserRole

        now = datetime.utcnow()
        today = now.date()

        # Get all regular users (exclude admin and manager)
        regular_users = db.query(User).filter(
            User.role == UserRole.USER,
            User.is_active == True
        ).all()

        daily_leaders = []
        weekly_leaders = []
        monthly_leaders = []

        print(f"Processing {len(regular_users)} regular users for leaderboard")

        for user in regular_users:
            try:
                # Sync user progress first
                AchievementService._sync_user_progress_with_requests(db, user.id)

                # Get user's current progress
                user_data = AchievementService.get_user_dashboard_data(db, user.id)
                current_progress = user_data.get("current_progress", {})

                # Extract progress for each timeframe with defaults
                daily_progress = current_progress.get("daily", {
                    "target": 10, "current": 0, "percentage": 0, "status": "لم يبدأ"
                })
                weekly_progress = current_progress.get("weekly", {
                    "target": 50, "current": 0, "percentage": 0, "status": "لم يبدأ"
                })
                monthly_progress = current_progress.get("monthly", {
                    "target": 200, "current": 0, "percentage": 0, "status": "لم يبدأ"
                })

                # Add all users to leaderboards (including those with 0 progress)
                daily_leaders.append({
                    "user": user,
                    "progress": daily_progress,
                    "sort_key": daily_progress.get("current", 0)
                })

                weekly_leaders.append({
                    "user": user,
                    "progress": weekly_progress,
                    "sort_key": weekly_progress.get("current", 0)
                })

                monthly_leaders.append({
                    "user": user,
                    "progress": monthly_progress,
                    "sort_key": monthly_progress.get("current", 0)
                })

            except Exception as e:
                print(f"Error processing user {user.username}: {e}")
                continue

        # Sort by current progress (descending), then by percentage, then by user ID for consistency
        def sort_key(item):
            return (
                item["sort_key"],  # Primary: current progress
                item["progress"].get("percentage", 0),  # Secondary: percentage
                -item["user"].id  # Tertiary: user ID (negative for consistent ordering)
            )

        daily_leaders.sort(key=sort_key, reverse=True)
        weekly_leaders.sort(key=sort_key, reverse=True)
        monthly_leaders.sort(key=sort_key, reverse=True)

        # Get top 3 for each category
        top_daily = daily_leaders[:3]
        top_weekly = weekly_leaders[:3]
        top_monthly = monthly_leaders[:3]

        print(f"Daily leaders: {len(top_daily)}, Weekly leaders: {len(top_weekly)}, Monthly leaders: {len(top_monthly)}")

        return {
            "daily_leaders": top_daily,
            "weekly_leaders": top_weekly,
            "monthly_leaders": top_monthly,
            "total_users": len(regular_users)
        }

    @staticmethod
    def get_user_dashboard_data(db: Session, user_id: int) -> Dict[str, Any]:
        """Get comprehensive achievement data for user dashboard"""
        now = datetime.utcnow()
        today = now.date()

        # Sync achievement progress with actual request data
        AchievementService._sync_user_progress_with_requests(db, user_id)

        # Get user stats
        user_stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
        if not user_stats:
            user_stats = UserStats(user_id=user_id)
            db.add(user_stats)
            db.commit()
            db.refresh(user_stats)

        # Get current period progress
        daily_progress = AchievementService._get_daily_progress(db, user_id, today)
        weekly_progress = AchievementService._get_weekly_progress(db, user_id, now)
        monthly_progress = AchievementService._get_monthly_progress(db, user_id, now)

        # Get recent achievements
        recent_achievements = db.query(UserAchievement).join(Achievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.is_completed == True
        ).order_by(desc(UserAchievement.completed_at)).limit(5).all()

        # Get active competitions
        active_competitions = AchievementService.get_active_competitions(db, user_id)

        # Get leaderboard position
        leaderboard_position = AchievementService.get_user_leaderboard_position(db, user_id)

        # Get real-time performance statistics
        performance_stats = AchievementService._get_user_performance_stats(db, user_id)

        return {
            "user_stats": {
                "total_points": user_stats.total_points,
                "current_streak": user_stats.current_daily_streak,
                "longest_streak": user_stats.longest_daily_streak,
                "total_achievements": user_stats.total_achievements,
                "global_rank": user_stats.global_rank or "غير مصنف"
            },
            "current_progress": {
                "daily": daily_progress,
                "weekly": weekly_progress,
                "monthly": monthly_progress
            },
            "performance_stats": performance_stats,
            "recent_achievements": [
                {
                    "name": ua.achievement.name,
                    "description": ua.achievement.description,
                    "badge_icon": ua.achievement.badge_icon,
                    "badge_color": ua.achievement.badge_color,
                    "points": ua.points_earned,
                    "completed_at": ua.completed_at
                }
                for ua in recent_achievements
            ],
            "active_competitions": active_competitions,
            "leaderboard_position": leaderboard_position
        }

    @staticmethod
    def _get_daily_progress(db: Session, user_id: int, today: date) -> Dict[str, Any]:
        """Get daily progress for user"""
        # Get daily achievements for today
        daily_achievements = db.query(UserAchievement).join(Achievement).filter(
            UserAchievement.user_id == user_id,
            Achievement.achievement_type == AchievementType.DAILY,
            func.date(UserAchievement.period_start) == today
        ).all()

        if not daily_achievements:
            return {
                "target": 10,
                "current": 0,
                "percentage": 0,
                "status": "لم يبدأ",
                "achievements": []
            }

        # Get the main daily target (10 requests)
        main_achievement = next((ua for ua in daily_achievements if ua.achievement.target_value == 10), None)
        if main_achievement:
            current = main_achievement.current_progress
            target = main_achievement.achievement.target_value
            percentage = min(100, (current / target) * 100)

            if main_achievement.is_completed:
                status = "مكتمل ✅"
            elif percentage >= 50:
                status = "في التقدم 🔥"
            else:
                status = "بداية اليوم 🌅"
        else:
            current = 0
            target = 10
            percentage = 0
            status = "لم يبدأ"

        return {
            "target": target,
            "current": current,
            "percentage": round(percentage, 1),
            "status": status,
            "achievements": [
                {
                    "name": ua.achievement.name,
                    "progress": ua.current_progress,
                    "target": ua.achievement.target_value,
                    "completed": ua.is_completed,
                    "badge_icon": ua.achievement.badge_icon
                }
                for ua in daily_achievements
            ]
        }

    @staticmethod
    def _get_weekly_progress(db: Session, user_id: int, now: datetime) -> Dict[str, Any]:
        """Get weekly progress for user"""
        # Get start of current week
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        weekly_achievements = db.query(UserAchievement).join(Achievement).filter(
            UserAchievement.user_id == user_id,
            Achievement.achievement_type == AchievementType.WEEKLY,
            UserAchievement.period_start == week_start
        ).all()

        if not weekly_achievements:
            return {
                "target": 50,
                "current": 0,
                "percentage": 0,
                "status": "لم يبدأ",
                "achievements": []
            }

        # Get the main weekly target (50 requests)
        main_achievement = next((ua for ua in weekly_achievements if ua.achievement.target_value == 50), None)
        if main_achievement:
            current = main_achievement.current_progress
            target = main_achievement.achievement.target_value
            percentage = min(100, (current / target) * 100)

            if main_achievement.is_completed:
                status = "مكتمل 🏆"
            elif percentage >= 70:
                status = "قريب من الهدف 🎯"
            elif percentage >= 30:
                status = "في التقدم 📈"
            else:
                status = "بداية الأسبوع 🚀"
        else:
            current = 0
            target = 50
            percentage = 0
            status = "لم يبدأ"

        return {
            "target": target,
            "current": current,
            "percentage": round(percentage, 1),
            "status": status,
            "achievements": [
                {
                    "name": ua.achievement.name,
                    "progress": ua.current_progress,
                    "target": ua.achievement.target_value,
                    "completed": ua.is_completed,
                    "badge_icon": ua.achievement.badge_icon
                }
                for ua in weekly_achievements
            ]
        }

    @staticmethod
    def _get_monthly_progress(db: Session, user_id: int, now: datetime) -> Dict[str, Any]:
        """Get monthly progress for user"""
        # Get start of current month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_achievements = db.query(UserAchievement).join(Achievement).filter(
            UserAchievement.user_id == user_id,
            Achievement.achievement_type == AchievementType.MONTHLY,
            UserAchievement.period_start == month_start
        ).all()

        if not monthly_achievements:
            return {
                "target": 200,
                "current": 0,
                "percentage": 0,
                "status": "لم يبدأ",
                "achievements": []
            }

        # Get the main monthly target (200 requests)
        main_achievement = next((ua for ua in monthly_achievements if ua.achievement.target_value == 200), None)
        if main_achievement:
            current = main_achievement.current_progress
            target = main_achievement.achievement.target_value
            percentage = min(100, (current / target) * 100)

            if main_achievement.is_completed:
                status = "مكتمل 👑"
            elif percentage >= 80:
                status = "قريب جداً من الهدف 🔥"
            elif percentage >= 50:
                status = "في منتصف الطريق 💪"
            elif percentage >= 25:
                status = "تقدم جيد 📊"
            else:
                status = "بداية الشهر 🌟"
        else:
            current = 0
            target = 200
            percentage = 0
            status = "لم يبدأ"

        return {
            "target": target,
            "current": current,
            "percentage": round(percentage, 1),
            "status": status,
            "achievements": [
                {
                    "name": ua.achievement.name,
                    "progress": ua.current_progress,
                    "target": ua.achievement.target_value,
                    "completed": ua.is_completed,
                    "badge_icon": ua.achievement.badge_icon
                }
                for ua in monthly_achievements
            ]
        }

    @staticmethod
    def get_active_competitions(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Get active competitions for user"""
        now = datetime.utcnow()

        active_competitions = db.query(Competition).filter(
            Competition.status == CompetitionStatus.ACTIVE,
            Competition.start_date <= now,
            Competition.end_date >= now
        ).all()

        competitions_data = []
        for competition in active_competitions:
            # Check if user is participating
            participant = db.query(CompetitionParticipant).filter(
                CompetitionParticipant.competition_id == competition.id,
                CompetitionParticipant.user_id == user_id
            ).first()

            # Get total participants
            total_participants = db.query(CompetitionParticipant).filter(
                CompetitionParticipant.competition_id == competition.id
            ).count()

            # Get user's rank if participating
            user_rank = None
            if participant:
                # Get participants ordered by progress
                participants = db.query(CompetitionParticipant).filter(
                    CompetitionParticipant.competition_id == competition.id
                ).order_by(desc(CompetitionParticipant.current_progress)).all()

                for i, p in enumerate(participants, 1):
                    if p.user_id == user_id:
                        user_rank = i
                        break

            competitions_data.append({
                "id": competition.id,
                "name": competition.name,
                "description": competition.description,
                "type": competition.competition_type.value,
                "target": competition.target_value,
                "end_date": competition.end_date,
                "is_participating": participant is not None,
                "user_progress": participant.current_progress if participant else 0,
                "user_rank": user_rank,
                "total_participants": total_participants,
                "time_remaining": competition.end_date - now
            })

        return competitions_data

    @staticmethod
    def get_user_leaderboard_position(db: Session, user_id: int) -> Dict[str, Any]:
        """Get user's position in various leaderboards"""
        # Global leaderboard (by total points)
        global_rank_query = db.query(UserStats).order_by(desc(UserStats.total_points)).all()
        global_rank = None
        for i, stats in enumerate(global_rank_query, 1):
            if stats.user_id == user_id:
                global_rank = i
                break

        # Daily leaderboard (by daily achievements today)
        today = datetime.utcnow().date()
        daily_progress = db.query(
            UserAchievement.user_id,
            func.sum(UserAchievement.current_progress).label('daily_total')
        ).join(Achievement).filter(
            Achievement.achievement_type == AchievementType.DAILY,
            func.date(UserAchievement.period_start) == today
        ).group_by(UserAchievement.user_id).order_by(desc('daily_total')).all()

        daily_rank = None
        for i, (uid, total) in enumerate(daily_progress, 1):
            if uid == user_id:
                daily_rank = i
                break

        return {
            "global_rank": global_rank or "غير مصنف",
            "daily_rank": daily_rank or "غير مصنف",
            "total_users": len(global_rank_query)
        }

    @staticmethod
    def get_leaderboard_data(db: Session, period: str = "global", limit: int = 50) -> List[Dict[str, Any]]:
        """Get leaderboard data for different periods"""
        if period == "global":
            return AchievementService._get_global_leaderboard(db, limit)
        elif period == "daily":
            return AchievementService._get_daily_leaderboard(db, limit)
        elif period == "weekly":
            return AchievementService._get_weekly_leaderboard(db, limit)
        elif period == "monthly":
            return AchievementService._get_monthly_leaderboard(db, limit)
        else:
            return []

    @staticmethod
    def _get_global_leaderboard(db: Session, limit: int) -> List[Dict[str, Any]]:
        """Get global leaderboard by total points"""
        leaderboard = db.query(UserStats, User).join(User).filter(
            User.role == UserRole.USER,
            User.is_active == True
        ).order_by(desc(UserStats.total_points)).limit(limit).all()

        return [
            {
                "rank": i + 1,
                "user_id": stats.user_id,
                "full_name": user.full_name,
                "username": user.username,
                "total_points": stats.total_points,
                "total_achievements": stats.total_achievements,
                "current_streak": stats.current_daily_streak,
                "longest_streak": stats.longest_daily_streak
            }
            for i, (stats, user) in enumerate(leaderboard)
        ]

    @staticmethod
    def _get_daily_leaderboard(db: Session, limit: int) -> List[Dict[str, Any]]:
        """Get daily leaderboard by today's progress"""
        today = datetime.utcnow().date()

        daily_progress = db.query(
            UserAchievement.user_id,
            User.full_name,
            User.username,
            func.sum(UserAchievement.current_progress).label('daily_total')
        ).join(Achievement).join(User).filter(
            Achievement.achievement_type == AchievementType.DAILY,
            func.date(UserAchievement.period_start) == today,
            User.role == UserRole.USER,
            User.is_active == True
        ).group_by(
            UserAchievement.user_id, User.full_name, User.username
        ).order_by(desc('daily_total')).limit(limit).all()

        return [
            {
                "rank": i + 1,
                "user_id": user_id,
                "full_name": full_name,
                "username": username,
                "daily_progress": int(daily_total),
                "target": 10,
                "percentage": min(100, (daily_total / 10) * 100)
            }
            for i, (user_id, full_name, username, daily_total) in enumerate(daily_progress)
        ]

    @staticmethod
    def _get_weekly_leaderboard(db: Session, limit: int) -> List[Dict[str, Any]]:
        """Get weekly leaderboard by this week's progress"""
        now = datetime.utcnow()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        weekly_progress = db.query(
            UserAchievement.user_id,
            User.full_name,
            User.username,
            func.sum(UserAchievement.current_progress).label('weekly_total')
        ).join(Achievement).join(User).filter(
            Achievement.achievement_type == AchievementType.WEEKLY,
            UserAchievement.period_start == week_start,
            User.role == UserRole.USER,
            User.is_active == True
        ).group_by(
            UserAchievement.user_id, User.full_name, User.username
        ).order_by(desc('weekly_total')).limit(limit).all()

        return [
            {
                "rank": i + 1,
                "user_id": user_id,
                "full_name": full_name,
                "username": username,
                "weekly_progress": int(weekly_total),
                "target": 50,
                "percentage": min(100, (weekly_total / 50) * 100)
            }
            for i, (user_id, full_name, username, weekly_total) in enumerate(weekly_progress)
        ]

    @staticmethod
    def _get_monthly_leaderboard(db: Session, limit: int) -> List[Dict[str, Any]]:
        """Get monthly leaderboard by this month's progress"""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_progress = db.query(
            UserAchievement.user_id,
            User.full_name,
            User.username,
            func.sum(UserAchievement.current_progress).label('monthly_total')
        ).join(Achievement).join(User).filter(
            Achievement.achievement_type == AchievementType.MONTHLY,
            UserAchievement.period_start == month_start,
            User.role == UserRole.USER,
            User.is_active == True
        ).group_by(
            UserAchievement.user_id, User.full_name, User.username
        ).order_by(desc('monthly_total')).limit(limit).all()

        return [
            {
                "rank": i + 1,
                "user_id": user_id,
                "full_name": full_name,
                "username": username,
                "monthly_progress": int(monthly_total),
                "target": 200,
                "percentage": min(100, (monthly_total / 200) * 100)
            }
            for i, (user_id, full_name, username, monthly_total) in enumerate(monthly_progress)
        ]

    @staticmethod
    def create_competition(db: Session, creator_id: int, competition_data: Dict[str, Any]) -> Competition:
        """Create a new competition"""
        competition = Competition(
            name=competition_data["name"],
            description=competition_data["description"],
            competition_type=AchievementType(competition_data["type"]),
            target_value=competition_data["target"],
            start_date=competition_data["start_date"],
            end_date=competition_data["end_date"],
            first_place_points=competition_data.get("first_place_points", 100),
            second_place_points=competition_data.get("second_place_points", 75),
            third_place_points=competition_data.get("third_place_points", 50),
            participation_points=competition_data.get("participation_points", 10),
            max_participants=competition_data.get("max_participants"),
            is_public=competition_data.get("is_public", True),
            created_by=creator_id,
            status=CompetitionStatus.UPCOMING
        )

        db.add(competition)
        db.commit()
        db.refresh(competition)

        return competition

    @staticmethod
    def join_competition(db: Session, competition_id: int, user_id: int) -> bool:
        """Join a competition"""
        # Check if competition exists and is joinable
        competition = db.query(Competition).filter(Competition.id == competition_id).first()
        if not competition or competition.status not in [CompetitionStatus.UPCOMING, CompetitionStatus.ACTIVE]:
            return False

        # Check if user is already participating
        existing = db.query(CompetitionParticipant).filter(
            CompetitionParticipant.competition_id == competition_id,
            CompetitionParticipant.user_id == user_id
        ).first()

        if existing:
            return False

        # Check participant limit
        if competition.max_participants:
            current_participants = db.query(CompetitionParticipant).filter(
                CompetitionParticipant.competition_id == competition_id
            ).count()

            if current_participants >= competition.max_participants:
                return False

        # Add participant
        participant = CompetitionParticipant(
            competition_id=competition_id,
            user_id=user_id
        )

        db.add(participant)
        db.commit()

        return True

    @staticmethod
    def get_competition_leaderboard(db: Session, competition_id: int) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific competition"""
        participants = db.query(CompetitionParticipant, User).join(User).filter(
            CompetitionParticipant.competition_id == competition_id
        ).order_by(desc(CompetitionParticipant.current_progress)).all()

        return [
            {
                "rank": i + 1,
                "user_id": participant.user_id,
                "full_name": user.full_name,
                "username": user.username,
                "progress": participant.current_progress,
                "last_updated": participant.last_updated
            }
            for i, (participant, user) in enumerate(participants)
        ]

    @staticmethod
    def update_rankings(db: Session):
        """Update global rankings for all users"""
        # Update global rankings
        users_by_points = db.query(UserStats).order_by(desc(UserStats.total_points)).all()
        for i, user_stats in enumerate(users_by_points, 1):
            user_stats.global_rank = i

        db.commit()
