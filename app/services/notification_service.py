from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging

from app.models.notification import (
    Notification, 
    NotificationType, 
    NotificationPriority,
    PushSubscription,
    NotificationPreference
)
from app.models.user import User
from app.models.request import Request, RequestStatus

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications and push notifications"""

    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        action_url: Optional[str] = None,
        request_id: Optional[int] = None,
        related_user_id: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Create a new notification"""
        try:
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                priority=priority,
                title=title,
                message=message,
                action_url=action_url,
                request_id=request_id,
                related_user_id=related_user_id,
                extra_data=extra_data
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Try to send push notification
            NotificationService._send_push_notification(db, notification)
            
            logger.info(f"Created notification {notification.id} for user {user_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def create_request_status_notification(
        db: Session,
        request: Request,
        old_status: RequestStatus,
        new_status: RequestStatus,
        admin_user_id: Optional[int] = None
    ) -> Optional[Notification]:
        """Create notification for request status change"""
        try:
            # Check if user wants these notifications
            if not NotificationService._should_send_notification(
                db, request.user_id, "request_status_notifications"
            ):
                return None

            # Generate appropriate message based on status change
            status_messages = {
                RequestStatus.PENDING: "تم تحديث حالة طلبك إلى: قيد الانتظار",
                RequestStatus.IN_PROGRESS: "تم تحديث حالة طلبك إلى: قيد المعالجة",
                RequestStatus.COMPLETED: "تم إكمال طلبك بنجاح! 🎉",
                RequestStatus.REJECTED: "تم رفض طلبك. يرجى مراجعة التفاصيل"
            }
            
            priority_map = {
                RequestStatus.COMPLETED: NotificationPriority.HIGH,
                RequestStatus.REJECTED: NotificationPriority.HIGH,
                RequestStatus.IN_PROGRESS: NotificationPriority.NORMAL,
                RequestStatus.PENDING: NotificationPriority.LOW
            }
            
            title = f"تحديث الطلب {request.request_number}"
            message = status_messages.get(new_status, f"تم تحديث حالة طلبك إلى: {new_status.value}")
            priority = priority_map.get(new_status, NotificationPriority.NORMAL)
            action_url = f"/requests/{request.id}/view"
            
            extra_data = {
                "old_status": old_status.value,
                "new_status": new_status.value,
                "request_number": request.request_number,
                "admin_user_id": admin_user_id
            }
            
            return NotificationService.create_notification(
                db=db,
                user_id=request.user_id,
                notification_type=NotificationType.REQUEST_STATUS_CHANGED,
                title=title,
                message=message,
                priority=priority,
                action_url=action_url,
                request_id=request.id,
                related_user_id=admin_user_id,
                extra_data=extra_data
            )
            
        except Exception as e:
            logger.error(f"Error creating request status notification: {str(e)}")
            return None

    @staticmethod
    def create_request_created_notification(
        db: Session,
        request: Request
    ) -> Optional[Notification]:
        """Create notification for new request creation"""
        try:
            # Check if user wants these notifications
            if not NotificationService._should_send_notification(
                db, request.user_id, "request_updates_notifications"
            ):
                return None

            title = "تم إنشاء طلب جديد"
            message = f"تم إنشاء طلبك {request.request_number} بنجاح وهو الآن قيد المراجعة"
            action_url = f"/requests/{request.id}/view"
            
            extra_data = {
                "request_number": request.request_number,
                "request_type": "new_request"
            }
            
            return NotificationService.create_notification(
                db=db,
                user_id=request.user_id,
                notification_type=NotificationType.REQUEST_CREATED,
                title=title,
                message=message,
                priority=NotificationPriority.NORMAL,
                action_url=action_url,
                request_id=request.id,
                extra_data=extra_data
            )
            
        except Exception as e:
            logger.error(f"Error creating request created notification: {str(e)}")
            return None

    @staticmethod
    def create_admin_message_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        admin_user_id: int,
        action_url: Optional[str] = None
    ) -> Optional[Notification]:
        """Create notification for admin message"""
        try:
            # Check if user wants these notifications
            if not NotificationService._should_send_notification(
                db, user_id, "admin_message_notifications"
            ):
                return None

            return NotificationService.create_notification(
                db=db,
                user_id=user_id,
                notification_type=NotificationType.ADMIN_MESSAGE,
                title=title,
                message=message,
                priority=NotificationPriority.HIGH,
                action_url=action_url,
                related_user_id=admin_user_id
            )

        except Exception as e:
            logger.error(f"Error creating admin message notification: {str(e)}")
            return None

    @staticmethod
    def create_user_approval_notification(
        db: Session,
        user_id: int,
        admin_user_id: int,
        approved: bool = True
    ) -> Optional[Notification]:
        """Create notification for user account approval or rejection"""
        try:
            # Check if user wants these notifications
            if not NotificationService._should_send_notification(
                db, user_id, "admin_message_notifications"
            ):
                return None

            if approved:
                title = "تم قبول حسابك! 🎉"
                message = "مرحباً بك! تم قبول حسابك من قبل الإدارة. يمكنك الآن تسجيل الدخول والبدء في استخدام النظام."
                priority = NotificationPriority.HIGH
                action_url = "/login"
            else:
                title = "تم رفض حسابك"
                message = "نأسف لإبلاغك أنه تم رفض طلب إنشاء حسابك من قبل الإدارة. يرجى التواصل مع الإدارة للمزيد من المعلومات."
                priority = NotificationPriority.HIGH
                action_url = "/login"

            extra_data = {
                "approval_status": "approved" if approved else "rejected",
                "admin_user_id": admin_user_id
            }

            return NotificationService.create_notification(
                db=db,
                user_id=user_id,
                notification_type=NotificationType.ADMIN_MESSAGE,
                title=title,
                message=message,
                priority=priority,
                action_url=action_url,
                related_user_id=admin_user_id,
                extra_data=extra_data
            )

        except Exception as e:
            logger.error(f"Error creating user approval notification: {str(e)}")
            return None

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        page: int = 1,
        per_page: int = 20,
        unread_only: bool = False
    ) -> Dict[str, Any]:
        """Get user's notifications with pagination"""
        try:
            query = db.query(Notification).filter(Notification.user_id == user_id)
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            notifications = query.order_by(desc(Notification.created_at)).offset(
                (page - 1) * per_page
            ).limit(per_page).all()
            
            return {
                "notifications": notifications,
                "total_count": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": (total_count + per_page - 1) // per_page
            }
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {str(e)}")
            return {
                "notifications": [],
                "total_count": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0
            }

    @staticmethod
    def mark_notification_as_read(db: Session, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read"""
        try:
            notification = db.query(Notification).filter(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            ).first()
            
            if notification and not notification.is_read:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                db.commit()
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def mark_all_notifications_as_read(db: Session, user_id: int) -> int:
        """Mark all user notifications as read"""
        try:
            updated_count = db.query(Notification).filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            ).update({
                "is_read": True,
                "read_at": datetime.utcnow()
            })
            
            db.commit()
            return updated_count
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            db.rollback()
            return 0

    @staticmethod
    def get_unread_count(db: Session, user_id: int) -> int:
        """Get count of unread notifications for user"""
        try:
            return db.query(Notification).filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            ).count()
            
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return 0

    @staticmethod
    def _should_send_notification(db: Session, user_id: int, preference_type: str) -> bool:
        """Check if user wants to receive this type of notification"""
        try:
            preferences = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).first()
            
            if not preferences:
                # Create default preferences
                preferences = NotificationService.create_default_preferences(db, user_id)
            
            # Check general notification settings
            if not preferences.in_app_notifications_enabled:
                return False
            
            # Check specific preference type
            return getattr(preferences, preference_type, True)
            
        except Exception as e:
            logger.error(f"Error checking notification preferences: {str(e)}")
            return True  # Default to sending notifications

    @staticmethod
    def create_default_preferences(db: Session, user_id: int) -> NotificationPreference:
        """Create default notification preferences for user"""
        try:
            preferences = NotificationPreference(user_id=user_id)
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
            return preferences
            
        except Exception as e:
            logger.error(f"Error creating default preferences: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def _send_push_notification(db: Session, notification: Notification):
        """Send push notification (placeholder for actual implementation)"""
        try:
            # Get user's push subscriptions
            subscriptions = db.query(PushSubscription).filter(
                and_(
                    PushSubscription.user_id == notification.user_id,
                    PushSubscription.is_active == True
                )
            ).all()
            
            if not subscriptions:
                return
            
            # Check if user wants push notifications
            preferences = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == notification.user_id
            ).first()
            
            if preferences and not preferences.push_notifications_enabled:
                return
            
            # TODO: Implement actual push notification sending
            # This would integrate with a service like Firebase Cloud Messaging
            # or Web Push Protocol
            
            logger.info(f"Would send push notification {notification.id} to {len(subscriptions)} devices")
            
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
