from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import logging
from app.models.user import User
from app.models.request import Request, RequestStatus
from app.models.activity import Activity, ActivityType

class ActivityService:
    _logger = logging.getLogger(__name__)

    @staticmethod
    def _normalize_timestamp(timestamp: datetime) -> datetime:
        """Normalize timestamp to UTC timezone-aware datetime"""
        if timestamp is None:
            return datetime.now(timezone.utc)

        if timestamp.tzinfo is None:
            # Assume naive datetime is UTC
            return timestamp.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC if timezone-aware
            return timestamp.astimezone(timezone.utc)

    @staticmethod
    def _get_status_arabic(status: str) -> str:
        """Get Arabic translation for request status"""
        status_map = {
            'pending': 'قيد الانتظار',
            'in_progress': 'قيد المعالجة',
            'completed': 'مكتمل',
            'rejected': 'مرفوض'
        }
        return status_map.get(status, status)

    @staticmethod
    def get_user_activities(
        db: Session,
        user_id: int,
        activity_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user activities with filtering"""
        try:
            activities = []
            
            # Parse date filters
            date_from_obj = None
            date_to_obj = None
            
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                except ValueError:
                    pass
            
            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                except ValueError:
                    pass
            
            # Get ONLY request activities - no other activity types
            request_activities = ActivityService._get_request_activities(
                db, user_id, activity_type, date_from_obj, date_to_obj
            )
            activities.extend(request_activities)
            
            # Sort by timestamp (newest first)
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Apply pagination
            return activities[skip:skip + limit]
            
        except Exception as e:
            ActivityService._logger.error(f"Error getting user activities for user {user_id}: {e}")
            return []

    @staticmethod
    def _get_request_activities(
        db: Session,
        user_id: int,
        activity_type: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get request-related activities"""
        activities = []

        try:
            # Debug logging
            ActivityService._logger.info(f"Getting request activities for user_id: {user_id}")

            # Base query for user's requests
            query = db.query(Request).filter(Request.user_id == user_id)

            # Apply date filters
            if date_from:
                query = query.filter(Request.created_at >= date_from)
            if date_to:
                query = query.filter(Request.created_at <= date_to)

            requests = query.order_by(desc(Request.created_at)).limit(50).all()
            ActivityService._logger.info(f"Found {len(requests)} requests for user_id: {user_id}")

            if not requests:
                # If no requests found, let's check if there are any requests at all for debugging
                all_requests = db.query(Request).limit(5).all()
                ActivityService._logger.info(f"No requests found for user {user_id}. Total requests in DB: {db.query(Request).count()}")
                if all_requests:
                    ActivityService._logger.info(f"Sample requests: {[(r.id, r.user_id, r.request_number) for r in all_requests]}")

            for req in requests:
                ActivityService._logger.info(f"Processing request {req.id} - {req.request_number} - Status: {req.status.value}")

                # Request created activity
                if not activity_type or activity_type == 'request_created':
                    activity = {
                        'id': f"req_created_{req.id}",
                        'type': 'request_created',
                        'title': 'إنشاء طلب جديد',
                        'description': f'تم إنشاء طلب رقم {req.request_number} للمبنى: {req.building_name or "غير محدد"}',
                        'details': {
                            'request_id': req.id,
                            'request_number': req.request_number,
                            'building_name': req.building_name,
                            'company_name': req.company_name,
                            'personal_number': req.personal_number,
                            'status': req.status.value,
                            'full_name': req.full_name or req.request_name
                        },
                        'timestamp': ActivityService._normalize_timestamp(req.created_at),
                        'icon': 'fas fa-plus-circle',
                        'color': 'text-green-600',
                        'bg_color': 'bg-green-50'
                    }
                    activities.append(activity)
                    ActivityService._logger.info(f"Added request_created activity for request {req.id}")
                
                # Request updated activity (if updated_at differs from created_at)
                if (not activity_type or activity_type == 'request_updated') and req.updated_at and req.updated_at != req.created_at:
                    # Calculate time difference to show meaningful updates
                    time_diff = (req.updated_at - req.created_at).total_seconds()
                    ActivityService._logger.info(f"Request {req.id} update check: time_diff={time_diff}, updated_at={req.updated_at}, created_at={req.created_at}")
                    if time_diff > 60:  # Only show updates that are more than 1 minute after creation
                        activity = {
                            'id': f"req_updated_{req.id}",
                            'type': 'request_updated',
                            'title': 'تحديث طلب',
                            'description': f'تم تحديث طلب رقم {req.request_number} - الحالة الحالية: {ActivityService._get_status_arabic(req.status.value)}',
                            'details': {
                                'request_id': req.id,
                                'request_number': req.request_number,
                                'building_name': req.building_name,
                                'company_name': req.company_name,
                                'status': req.status.value,
                                'status_arabic': ActivityService._get_status_arabic(req.status.value),
                                'update_time_diff': f'{int(time_diff / 3600)} ساعة' if time_diff > 3600 else f'{int(time_diff / 60)} دقيقة'
                            },
                            'timestamp': ActivityService._normalize_timestamp(req.updated_at),
                            'icon': 'fas fa-edit',
                            'color': 'text-blue-600',
                            'bg_color': 'bg-blue-50'
                        }
                        activities.append(activity)
                        ActivityService._logger.info(f"Added request_updated activity for request {req.id}")

                # Request completed activity
                if (not activity_type or activity_type == 'request_completed') and req.status.value == 'completed':
                    completion_time = req.updated_at or req.created_at
                    processing_time = (completion_time - req.created_at).total_seconds() if req.updated_at else 0

                    activity = {
                        'id': f"req_completed_{req.id}",
                        'type': 'request_completed',
                        'title': 'إكمال طلب',
                        'description': f'تم إكمال طلب رقم {req.request_number} للمبنى: {req.building_name or "غير محدد"}',
                        'details': {
                            'request_id': req.id,
                            'request_number': req.request_number,
                            'building_name': req.building_name,
                            'company_name': req.company_name,
                            'full_name': req.full_name or req.request_name,
                            'status': req.status.value,
                            'processing_time': f'{int(processing_time / 86400)} يوم' if processing_time > 86400 else f'{int(processing_time / 3600)} ساعة' if processing_time > 3600 else 'أقل من ساعة',
                            'completion_date': completion_time.strftime('%Y-%m-%d %H:%M')
                        },
                        'timestamp': ActivityService._normalize_timestamp(completion_time),
                        'icon': 'fas fa-check-circle',
                        'color': 'text-green-600',
                        'bg_color': 'bg-green-50'
                    }
                    activities.append(activity)
                    ActivityService._logger.info(f"Added request_completed activity for request {req.id}")

                # Request rejected activity
                if (not activity_type or activity_type == 'request_rejected') and req.status.value == 'rejected':
                    rejection_time = req.updated_at or req.created_at

                    activities.append({
                        'id': f"req_rejected_{req.id}",
                        'type': 'request_rejected',
                        'title': 'رفض طلب',
                        'description': f'تم رفض طلب رقم {req.request_number} للمبنى: {req.building_name or "غير محدد"}',
                        'details': {
                            'request_id': req.id,
                            'request_number': req.request_number,
                            'building_name': req.building_name,
                            'company_name': req.company_name,
                            'full_name': req.full_name or req.request_name,
                            'status': req.status.value,
                            'rejection_date': rejection_time.strftime('%Y-%m-%d %H:%M'),
                            'reason': 'لم يتم تحديد السبب'  # Could be enhanced with actual rejection reason
                        },
                        'timestamp': ActivityService._normalize_timestamp(rejection_time),
                        'icon': 'fas fa-times-circle',
                        'color': 'text-red-600',
                        'bg_color': 'bg-red-50'
                    })
            
        except Exception as e:
            ActivityService._logger.error(f"Error getting request activities: {e}")

        ActivityService._logger.info(f"Generated {len(activities)} request activities for user {user_id}")
        return activities

    @staticmethod
    def _get_user_activities(
        db: Session,
        user_id: int,
        activity_type: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get user-related activities"""
        activities = []
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return activities
            
            # Profile updated activity
            if (not activity_type or activity_type == 'profile_updated') and user.updated_at:
                if not date_from or user.updated_at >= date_from:
                    if not date_to or user.updated_at <= date_to:
                        activities.append({
                            'id': f"profile_updated_{user.id}",
                            'type': 'profile_updated',
                            'title': 'تحديث الملف الشخصي',
                            'description': 'تم تحديث معلومات الملف الشخصي',
                            'details': {
                                'user_id': user.id,
                                'full_name': user.full_name,
                                'email': user.email
                            },
                            'timestamp': ActivityService._normalize_timestamp(user.updated_at),
                            'icon': 'fas fa-user-edit',
                            'color': 'text-purple-600',
                            'bg_color': 'bg-purple-50'
                        })
            
            # Login activity (simulated - multiple logins)
            if not activity_type or activity_type == 'login':
                # Simulate multiple login activities
                login_times = [
                    user.created_at,  # First login (account creation)
                ]

                # Add some recent login activities
                if user.updated_at and user.updated_at != user.created_at:
                    login_times.append(user.updated_at)

                # Add simulated login from last week
                from datetime import timedelta
                recent_login = datetime.now(timezone.utc) - timedelta(days=3, hours=2)
                if not date_from or recent_login >= date_from:
                    if not date_to or recent_login <= date_to:
                        login_times.append(recent_login)

                for i, login_time in enumerate(login_times):
                    if not date_from or login_time >= date_from:
                        if not date_to or login_time <= date_to:
                            activities.append({
                                'id': f"login_{user.id}_{i}",
                                'type': 'login',
                                'title': 'تسجيل دخول',
                                'description': 'تم تسجيل الدخول إلى النظام',
                                'details': {
                                    'user_id': user.id,
                                    'username': user.username,
                                    'login_number': i + 1
                                },
                                'timestamp': ActivityService._normalize_timestamp(login_time),
                                'icon': 'fas fa-sign-in-alt',
                                'color': 'text-indigo-600',
                                'bg_color': 'bg-indigo-50'
                            })
            
            # Avatar uploaded activity (simulated)
            if not activity_type or activity_type == 'avatar_uploaded':
                # Check if user has avatar (this is a simplified check)
                from app.services.avatar_service import AvatarService
                avatar_url = AvatarService.get_avatar_url(user.id, user.full_name, db)
                if avatar_url and not avatar_url.startswith('https://ui-avatars.com'):
                    # User has uploaded avatar
                    timestamp = user.updated_at or user.created_at
                    if not date_from or timestamp >= date_from:
                        if not date_to or timestamp <= date_to:
                            activities.append({
                                'id': f"avatar_uploaded_{user.id}",
                                'type': 'avatar_uploaded',
                                'title': 'رفع صورة شخصية',
                                'description': 'تم رفع صورة شخصية جديدة',
                                'details': {
                                    'user_id': user.id,
                                    'avatar_url': avatar_url
                                },
                                'timestamp': ActivityService._normalize_timestamp(timestamp),
                                'icon': 'fas fa-camera',
                                'color': 'text-pink-600',
                                'bg_color': 'bg-pink-50'
                            })
            
        except Exception as e:
            ActivityService._logger.error(f"Error getting user activities: {e}")
        
        return activities

    @staticmethod
    def _get_file_activities(
        db: Session,
        user_id: int,
        activity_type: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get file upload activities"""
        activities = []

        try:
            # Get requests with files
            requests_with_files = db.query(Request).filter(
                Request.user_id == user_id,
                Request.files.isnot(None),
                Request.files != ''
            ).all()

            for req in requests_with_files:
                if req.files:
                    # Parse files (assuming JSON format)
                    try:
                        import json
                        files = json.loads(req.files) if isinstance(req.files, str) else req.files
                        if files:
                            timestamp = req.created_at
                            if not date_from or timestamp >= date_from:
                                if not date_to or timestamp <= date_to:
                                    file_count = len(files) if isinstance(files, list) else 1
                                    # Get file types for better description
                                    file_types = []
                                    if isinstance(files, list):
                                        for file_info in files:
                                            if isinstance(file_info, dict) and 'filename' in file_info:
                                                ext = file_info['filename'].split('.')[-1].lower()
                                                if ext not in file_types:
                                                    file_types.append(ext)

                                    file_types_str = ', '.join(file_types) if file_types else 'متنوعة'

                                    activities.append({
                                        'id': f"file_uploaded_{req.id}",
                                        'type': 'file_uploaded',
                                        'title': 'رفع ملفات للطلب',
                                        'description': f'تم رفع {file_count} ملف ({file_types_str}) مع طلب رقم {req.request_number} - {req.building_name or "غير محدد"}',
                                        'details': {
                                            'request_id': req.id,
                                            'request_number': req.request_number,
                                            'building_name': req.building_name,
                                            'file_count': file_count,
                                            'file_types': file_types_str,
                                            'files': files,
                                            'upload_date': timestamp.strftime('%Y-%m-%d %H:%M')
                                        },
                                        'timestamp': ActivityService._normalize_timestamp(timestamp),
                                        'icon': 'fas fa-file-upload',
                                        'color': 'text-orange-600',
                                        'bg_color': 'bg-orange-50'
                                    })
                    except:
                        pass

        except Exception as e:
            ActivityService._logger.error(f"Error getting file activities: {e}")

        return activities

    @staticmethod
    def get_user_activity_statistics(db: Session, user_id: int) -> Dict[str, Any]:
        """Get activity statistics for a user"""
        try:
            now = datetime.now(timezone.utc)
            
            # Get total requests count
            total_requests = db.query(Request).filter(Request.user_id == user_id).count()
            
            # Get activities in last 30 days
            thirty_days_ago = now - timedelta(days=30)
            recent_requests = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= thirty_days_ago
            ).count()
            
            # Get activities in last 7 days
            seven_days_ago = now - timedelta(days=7)
            weekly_requests = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= seven_days_ago
            ).count()
            
            # Get activities today
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_requests = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= today_start
            ).count()
            
            # Calculate activity level
            if daily_requests > 0:
                activity_level = "نشط جداً"
                activity_color = "text-green-600"
            elif weekly_requests > 0:
                activity_level = "نشط"
                activity_color = "text-blue-600"
            elif recent_requests > 0:
                activity_level = "نشط أحياناً"
                activity_color = "text-yellow-600"
            else:
                activity_level = "غير نشط"
                activity_color = "text-gray-600"
            
            return {
                'total_activities': total_requests,
                'recent_activities': recent_requests,
                'weekly_activities': weekly_requests,
                'daily_activities': daily_requests,
                'activity_level': activity_level,
                'activity_color': activity_color,
                'last_activity': None  # Will be calculated from activities
            }
            
        except Exception as e:
            ActivityService._logger.error(f"Error getting user activity statistics for user {user_id}: {e}")
            return {
                'total_activities': 0,
                'recent_activities': 0,
                'weekly_activities': 0,
                'daily_activities': 0,
                'activity_level': 'غير معروف',
                'activity_color': 'text-gray-600',
                'last_activity': None
            }

    @staticmethod
    def get_system_activity_statistics(db: Session) -> Dict[str, Any]:
        """Get system-wide activity statistics"""
        try:
            now = datetime.now(timezone.utc)

            # Get all users
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active == True).count()

            # Get total requests
            total_requests = db.query(Request).count()

            # Get activities today
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_requests = db.query(Request).filter(Request.created_at >= today_start).count()

            # Get daily active users with details
            daily_active_users = db.query(User).join(Request, User.id == Request.user_id).filter(
                Request.created_at >= today_start
            ).distinct().all()

            # Get activities this week
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            weekly_requests = db.query(Request).filter(Request.created_at >= week_start).count()

            # Get weekly active users with details
            weekly_active_users = db.query(User).join(Request, User.id == Request.user_id).filter(
                Request.created_at >= week_start
            ).distinct().all()

            # Get activities this month
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_requests = db.query(Request).filter(Request.created_at >= month_start).count()

            # Get monthly active users with details
            monthly_active_users = db.query(User).join(Request, User.id == Request.user_id).filter(
                Request.created_at >= month_start
            ).distinct().all()

            # Get request status breakdown
            status_breakdown = {}
            for status in RequestStatus:
                count = db.query(Request).filter(Request.status == status).count()
                status_breakdown[status.value] = count

            # Get most active users (top 5)
            most_active_users = []
            try:
                user_activity_counts = db.query(
                    Request.user_id,
                    func.count(Request.id).label('request_count'),
                    User.full_name,
                    User.email
                ).join(User, Request.user_id == User.id).group_by(
                    Request.user_id, User.full_name, User.email
                ).order_by(func.count(Request.id).desc()).limit(5).all()

                for user_data in user_activity_counts:
                    most_active_users.append({
                        'user_id': user_data.user_id,
                        'full_name': user_data.full_name,
                        'email': user_data.email,
                        'request_count': user_data.request_count
                    })
            except Exception as e:
                ActivityService._logger.warning(f"Error getting most active users: {e}")

            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_requests': total_requests,
                'daily': {
                    'requests': daily_requests,
                    'active_users_count': len(daily_active_users),
                    'active_users': [{'id': u.id, 'full_name': u.full_name, 'email': u.email} for u in daily_active_users]
                },
                'weekly': {
                    'requests': weekly_requests,
                    'active_users_count': len(weekly_active_users),
                    'active_users': [{'id': u.id, 'full_name': u.full_name, 'email': u.email} for u in weekly_active_users]
                },
                'monthly': {
                    'requests': monthly_requests,
                    'active_users_count': len(monthly_active_users),
                    'active_users': [{'id': u.id, 'full_name': u.full_name, 'email': u.email} for u in monthly_active_users]
                },
                'status_breakdown': status_breakdown,
                'most_active_users': most_active_users
            }

        except Exception as e:
            ActivityService._logger.error(f"Error getting system activity statistics: {e}")
            return {
                'total_users': 0,
                'active_users': 0,
                'total_requests': 0,
                'daily': {'requests': 0, 'active_users_count': 0, 'active_users': []},
                'weekly': {'requests': 0, 'active_users_count': 0, 'active_users': []},
                'monthly': {'requests': 0, 'active_users_count': 0, 'active_users': []},
                'status_breakdown': {},
                'most_active_users': []
            }

    @staticmethod
    def generate_user_activity_report(db: Session, period_months: int = 3) -> Dict[str, Any]:
        """Generate comprehensive user activity report for specified period"""
        try:
            ActivityService._logger.info(f"Starting report generation for {period_months} months")
            now = datetime.now(timezone.utc)  # Use UTC timezone to match database
            period_start = now - timedelta(days=period_months * 30)  # Approximate months to days

            ActivityService._logger.info(f"Date range: {period_start} to {now}")

            # Get all users
            all_users = db.query(User).filter(User.is_active == True).all()
            ActivityService._logger.info(f"Found {len(all_users)} active users")

            user_reports = []

            for user in all_users:
                # Get user's requests in the period
                user_requests = db.query(Request).filter(
                    Request.user_id == user.id,
                    Request.created_at >= period_start
                ).all()

                if len(user_requests) > 0:
                    ActivityService._logger.info(f"User {user.username} has {len(user_requests)} requests in period")

                # Calculate daily averages (requests per day)
                total_days = (now - period_start).days
                daily_average = len(user_requests) / max(total_days, 1)

                # Calculate weekly statistics
                weekly_requests = []
                current_week_start = period_start
                while current_week_start < now:
                    week_end = current_week_start + timedelta(days=7)
                    week_requests = [r for r in user_requests if current_week_start <= r.created_at < week_end]
                    weekly_requests.append(len(week_requests))
                    current_week_start = week_end

                # Calculate monthly statistics
                monthly_requests = []
                current_month = period_start.replace(day=1)
                while current_month < now:
                    # Get next month
                    if current_month.month == 12:
                        next_month = current_month.replace(year=current_month.year + 1, month=1)
                    else:
                        next_month = current_month.replace(month=current_month.month + 1)

                    month_requests = [r for r in user_requests if current_month <= r.created_at < next_month]
                    monthly_requests.append({
                        'month': current_month.strftime('%Y-%m'),
                        'month_name': current_month.strftime('%B %Y'),
                        'count': len(month_requests)
                    })
                    current_month = next_month

                # Get recent activity (last 30 days)
                recent_start = now - timedelta(days=30)
                recent_requests = [r for r in user_requests if r.created_at >= recent_start]

                # Get status breakdown for this user
                status_breakdown = {}
                for status in RequestStatus:
                    count = len([r for r in user_requests if r.status == status])
                    if count > 0:
                        status_breakdown[status.value] = count

                # Calculate first and last request dates safely
                first_request = min([r.created_at for r in user_requests]) if user_requests else None
                last_request = max([r.created_at for r in user_requests]) if user_requests else None

                user_report = {
                    'user_id': user.id,
                    'name': user.full_name,
                    'email': user.email,
                    'username': user.username,
                    'total_requests': len(user_requests),
                    'daily_average': round(daily_average, 2),
                    'weekly_requests': weekly_requests,
                    'weekly_average': round(sum(weekly_requests) / max(len(weekly_requests), 1), 2),
                    'monthly_requests': monthly_requests,
                    'monthly_average': round(sum([m['count'] for m in monthly_requests]) / max(len(monthly_requests), 1), 2),
                    'recent_requests': len(recent_requests),
                    'status_breakdown': status_breakdown,
                    'first_request': first_request.isoformat() if first_request else None,
                    'last_request': last_request.isoformat() if last_request else None,
                    'first_request_date': first_request.isoformat() if first_request else None,  # Convert to string for JSON
                    'last_request_date': last_request.isoformat() if last_request else None,    # Convert to string for JSON
                    'first_request_datetime': first_request,  # Keep original datetime for template only
                    'last_request_datetime': last_request,    # Keep original datetime for template only
                    'activity_level': 'نشط جداً' if daily_average > 1 else 'نشط' if daily_average > 0.5 else 'نشط أحياناً' if daily_average > 0.1 else 'غير نشط'
                }

                user_reports.append(user_report)

            # Sort by total requests (most active first)
            user_reports.sort(key=lambda x: x['total_requests'], reverse=True)

            # Calculate summary statistics
            total_requests_in_period = sum([ur['total_requests'] for ur in user_reports])
            active_users_count = len([ur for ur in user_reports if ur['total_requests'] > 0])

            ActivityService._logger.info(f"Report completed: {len(user_reports)} users, {total_requests_in_period} total requests")

            # Create a JSON-safe version of the report
            json_safe_user_reports = []
            for user_report in user_reports:
                # Create a copy without the datetime objects
                json_safe_report = {k: v for k, v in user_report.items()
                                  if k not in ['first_request_datetime', 'last_request_datetime']}
                json_safe_user_reports.append(json_safe_report)

            return {
                'period_months': period_months,
                'period_start': period_start.isoformat(),
                'period_end': now.isoformat(),
                'period_start_datetime': period_start,  # Keep for template
                'period_end_datetime': now,             # Keep for template
                'total_users': len(user_reports),
                'active_users': active_users_count,
                'inactive_users': len(user_reports) - active_users_count,
                'total_requests': total_requests_in_period,
                'average_requests_per_user': round(total_requests_in_period / max(len(user_reports), 1), 2),
                'user_reports': json_safe_user_reports,
                'user_reports_with_datetime': user_reports,  # Keep full version for template
                'generated_at': now.isoformat(),
                'generated_at_datetime': now  # Keep for template
            }

        except Exception as e:
            ActivityService._logger.error(f"Error generating user activity report: {e}")
            # Return safe default values even on error
            now = datetime.now(timezone.utc)  # Use UTC timezone to match database
            period_start = now - timedelta(days=period_months * 30)
            return {
                'period_months': period_months,
                'period_start': period_start,
                'period_end': now,
                'total_users': 0,
                'active_users': 0,
                'inactive_users': 0,
                'total_requests': 0,
                'average_requests_per_user': 0,
                'user_reports': [],
                'generated_at': now,
                'error': str(e)
            }

    @staticmethod
    def get_all_activities(
        db: Session,
        activity_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all activities across all users with filtering"""
        try:
            all_activities = []

            # Parse date filters
            date_from_obj = None
            date_to_obj = None

            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                except ValueError:
                    pass

            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                except ValueError:
                    pass

            # Get all users (for search filtering)
            users_query = db.query(User)
            if search_query:
                users_query = users_query.filter(
                    (User.full_name.ilike(f"%{search_query}%")) |
                    (User.email.ilike(f"%{search_query}%")) |
                    (User.username.ilike(f"%{search_query}%"))
                )

            users = users_query.all()

            # Get activities for each user
            for user in users:
                user_activities = ActivityService.get_user_activities(
                    db=db,
                    user_id=user.id,
                    activity_type=activity_type,
                    date_from=date_from,
                    date_to=date_to,
                    limit=1000,  # Get more activities per user for sorting
                    skip=0
                )

                # Add user info to each activity
                for activity in user_activities:
                    activity['user'] = {
                        'id': user.id,
                        'full_name': user.full_name,
                        'email': user.email,
                        'username': user.username,
                        'role': user.role.value if user.role else 'user'
                    }

                all_activities.extend(user_activities)

            # Sort by timestamp (newest first)
            all_activities.sort(key=lambda x: x['timestamp'], reverse=True)

            # Apply pagination
            return all_activities[skip:skip + limit]

        except Exception as e:
            ActivityService._logger.error(f"Error getting all activities: {e}")
            return []

    @staticmethod
    def log_activity(
        db: Session,
        user_id: int,
        activity_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Log a new activity for a user"""
        try:
            # Convert activity_type string to ActivityType enum if needed
            if isinstance(activity_type, str):
                # Map common activity types
                activity_type_mapping = {
                    'request_created': ActivityType.REQUEST_CREATED,
                    'request_updated': ActivityType.REQUEST_UPDATED,
                    'request_completed': ActivityType.REQUEST_COMPLETED,
                    'request_rejected': ActivityType.REQUEST_REJECTED,
                    'file_uploaded': ActivityType.FILE_UPLOADED,
                    'file_deleted': ActivityType.FILE_DELETED,
                    'login': ActivityType.LOGIN,
                    'logout': ActivityType.LOGOUT,
                    'profile_updated': ActivityType.PROFILE_UPDATED,
                    'avatar_uploaded': ActivityType.AVATAR_UPLOADED,
                    'password_changed': ActivityType.PASSWORD_CHANGED,
                    'cross_user_request_viewed': ActivityType.CROSS_USER_REQUEST_VIEWED,
                    'cross_user_request_edited': ActivityType.CROSS_USER_REQUEST_EDITED,
                    'cross_user_request_status_updated': ActivityType.CROSS_USER_REQUEST_STATUS_UPDATED,
                    'cross_user_file_accessed': ActivityType.CROSS_USER_FILE_ACCESSED,
                    'cross_user_file_deleted': ActivityType.CROSS_USER_FILE_DELETED
                }

                activity_type_enum = activity_type_mapping.get(activity_type)
                if not activity_type_enum:
                    # Default to a generic type
                    ActivityService._logger.warning(f"Unknown activity type: {activity_type}, defaulting to PROFILE_UPDATED")
                    activity_type_enum = ActivityType.PROFILE_UPDATED
            else:
                activity_type_enum = activity_type

            # Create new activity record
            new_activity = Activity(
                user_id=user_id,
                activity_type=activity_type_enum,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc)
            )

            # Add details if the column exists
            if hasattr(Activity, 'details'):
                new_activity.details = details or {}

            # Add to session
            db.add(new_activity)

            # Commit with error handling
            try:
                db.commit()
                ActivityService._logger.info(f"Activity logged for user {user_id}: {activity_type} - {description}")
                return True
            except Exception as commit_error:
                ActivityService._logger.error(f"Error committing activity: {commit_error}")
                db.rollback()
                return False

        except Exception as e:
            ActivityService._logger.error(f"Error logging activity for user {user_id}: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_real_activities(
        db: Session,
        activity_type: Optional[str] = None,
        user_search: Optional[str] = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Activity]:
        """Get real activities from the database with filtering and pagination"""
        try:
            # Start with a simple activities query to avoid join issues
            query = db.query(Activity)

            # Filter by activity type
            if activity_type and activity_type != 'all' and activity_type.strip():
                try:
                    # Clean the activity type and try to match it
                    clean_activity_type = activity_type.strip().lower()

                    # Try to find matching ActivityType
                    activity_type_enum = None
                    for at in ActivityType:
                        if at.value.lower() == clean_activity_type:
                            activity_type_enum = at
                            break

                    if activity_type_enum:
                        query = query.filter(Activity.activity_type == activity_type_enum)
                    else:
                        ActivityService._logger.warning(f"Invalid activity type: {activity_type}")
                        # Don't filter by activity type if invalid, just log and continue

                except Exception as e:
                    ActivityService._logger.warning(f"Error processing activity type '{activity_type}': {e}")
                    # Don't filter by activity type if there's an error

            # Skip user search for now to avoid transaction issues
            if user_search and user_search.strip():
                ActivityService._logger.info(f"User search requested but temporarily disabled: {user_search}")
                # TODO: Re-enable user search once transaction issues are resolved

            # Order by most recent first
            query = query.order_by(Activity.created_at.desc())

            # Apply pagination
            query = query.offset(skip).limit(limit)

            return query.all()

        except Exception as e:
            ActivityService._logger.error(f"Error getting real activities: {e}")
            return []

    @staticmethod
    def get_activity_type_counts(db: Session) -> Dict[str, int]:
        """Get count of activities by type"""
        try:
            counts = {}
            for activity_type in ActivityType:
                count = db.query(Activity).filter(
                    Activity.activity_type == activity_type
                ).count()
                counts[activity_type.value] = count
            return counts
        except Exception as e:
            ActivityService._logger.error(f"Error getting activity type counts: {e}")
            return {}

    @staticmethod
    def get_total_activities_count(
        db: Session,
        activity_type: Optional[str] = None,
        user_search: Optional[str] = None
    ) -> int:
        """Get total count of activities with filters"""
        try:
            # Start with a simple activities query to avoid join issues
            query = db.query(Activity)

            # Filter by activity type
            if activity_type and activity_type != 'all' and activity_type.strip():
                try:
                    # Clean the activity type and try to match it
                    clean_activity_type = activity_type.strip().lower()

                    # Try to find matching ActivityType
                    activity_type_enum = None
                    for at in ActivityType:
                        if at.value.lower() == clean_activity_type:
                            activity_type_enum = at
                            break

                    if activity_type_enum:
                        query = query.filter(Activity.activity_type == activity_type_enum)
                    else:
                        ActivityService._logger.warning(f"Invalid activity type for count: {activity_type}")
                        # Don't filter by activity type if invalid, just log and continue

                except Exception as e:
                    ActivityService._logger.warning(f"Error processing activity type for count '{activity_type}': {e}")
                    # Don't filter by activity type if there's an error

            # Skip user search for now to avoid transaction issues
            if user_search and user_search.strip():
                ActivityService._logger.info(f"User search requested in count but temporarily disabled: {user_search}")
                # TODO: Re-enable user search once transaction issues are resolved

            return query.count()

        except Exception as e:
            ActivityService._logger.error(f"Error getting total activities count: {e}")
            return 0
