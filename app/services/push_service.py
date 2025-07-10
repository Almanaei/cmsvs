from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Dict, Any, List
import json
import logging
from datetime import datetime

from app.models.notification import PushSubscription, NotificationPreference
from app.models.user import User
from app.config import settings

try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    webpush = None
    WebPushException = Exception

logger = logging.getLogger(__name__)


class PushService:
    """Service for managing browser push notifications"""

    @staticmethod
    def subscribe_user(
        db: Session,
        user_id: int,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        user_agent: Optional[str] = None,
        device_name: Optional[str] = None
    ) -> PushSubscription:
        """Subscribe user to push notifications"""
        try:
            # Check if subscription already exists
            existing_subscription = db.query(PushSubscription).filter(
                and_(
                    PushSubscription.user_id == user_id,
                    PushSubscription.endpoint == endpoint
                )
            ).first()
            
            if existing_subscription:
                # Update existing subscription
                existing_subscription.p256dh_key = p256dh_key
                existing_subscription.auth_key = auth_key
                existing_subscription.user_agent = user_agent
                existing_subscription.device_name = device_name
                existing_subscription.is_active = True
                existing_subscription.last_used = datetime.utcnow()
                existing_subscription.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(existing_subscription)
                
                logger.info(f"Updated push subscription for user {user_id}")
                return existing_subscription
            
            # Create new subscription
            subscription = PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh_key=p256dh_key,
                auth_key=auth_key,
                user_agent=user_agent,
                device_name=device_name
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            logger.info(f"Created new push subscription for user {user_id}")
            return subscription
            
        except Exception as e:
            logger.error(f"Error subscribing user to push notifications: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def unsubscribe_user(
        db: Session,
        user_id: int,
        endpoint: Optional[str] = None
    ) -> bool:
        """Unsubscribe user from push notifications"""
        try:
            query = db.query(PushSubscription).filter(
                PushSubscription.user_id == user_id
            )
            
            if endpoint:
                query = query.filter(PushSubscription.endpoint == endpoint)
            
            subscriptions = query.all()
            
            for subscription in subscriptions:
                subscription.is_active = False
                subscription.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Unsubscribed user {user_id} from push notifications")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing user from push notifications: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def get_user_subscriptions(db: Session, user_id: int) -> List[PushSubscription]:
        """Get all active push subscriptions for user"""
        try:
            return db.query(PushSubscription).filter(
                and_(
                    PushSubscription.user_id == user_id,
                    PushSubscription.is_active == True
                )
            ).all()
            
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {str(e)}")
            return []

    @staticmethod
    def update_notification_preferences(
        db: Session,
        user_id: int,
        preferences: Dict[str, Any]
    ) -> Optional[NotificationPreference]:
        """Update user notification preferences"""
        try:
            # Get or create preferences
            user_preferences = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).first()
            
            if not user_preferences:
                user_preferences = NotificationPreference(user_id=user_id)
                db.add(user_preferences)
            
            # Update preferences
            for key, value in preferences.items():
                if hasattr(user_preferences, key):
                    setattr(user_preferences, key, value)
            
            user_preferences.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(user_preferences)
            
            logger.info(f"Updated notification preferences for user {user_id}")
            return user_preferences
            
        except Exception as e:
            logger.error(f"Error updating notification preferences: {str(e)}")
            db.rollback()
            return None

    @staticmethod
    def get_notification_preferences(db: Session, user_id: int) -> Optional[NotificationPreference]:
        """Get user notification preferences"""
        try:
            preferences = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).first()
            
            if not preferences:
                # Create default preferences
                preferences = NotificationPreference(user_id=user_id)
                db.add(preferences)
                db.commit()
                db.refresh(preferences)
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting notification preferences: {str(e)}")
            return None

    @staticmethod
    def send_push_notification(
        subscription: PushSubscription,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        icon: Optional[str] = None,
        badge: Optional[str] = None
    ) -> bool:
        """Send push notification to a specific subscription"""
        try:
            # Check if webpush is available
            if not WEBPUSH_AVAILABLE:
                logger.warning("pywebpush not available, skipping push notification")
                return False

            # Check if VAPID keys are configured
            if not settings.vapid_private_key or not settings.vapid_public_key:
                logger.warning("VAPID keys not configured, skipping push notification")
                return False

            # Prepare notification payload
            payload = {
                "title": title,
                "body": message,
                "icon": icon or "/static/icons/notification-icon.png",
                "badge": badge or "/static/icons/badge-icon.png",
                "data": {
                    "url": action_url or "/",
                    "timestamp": datetime.utcnow().isoformat()
                },
                "actions": [
                    {
                        "action": "view",
                        "title": "عرض",
                        "icon": "/static/icons/view-icon.png"
                    },
                    {
                        "action": "dismiss",
                        "title": "إغلاق",
                        "icon": "/static/icons/close-icon.png"
                    }
                ],
                "requireInteraction": True,
                "silent": False
            }

            # Send push notification using pywebpush
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {
                            "p256dh": subscription.p256dh_key,
                            "auth": subscription.auth_key
                        }
                    },
                    data=json.dumps(payload),
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims={
                        "sub": f"mailto:{settings.vapid_email}"
                    }
                )
                logger.info(f"Push notification sent successfully: {title}")
                return True

            except WebPushException as e:
                logger.error(f"Push notification failed: {str(e)}")
                # Mark subscription as inactive if it's invalid
                if "410" in str(e) or "invalid" in str(e).lower():
                    subscription.is_active = False
                return False

        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
            return False

    @staticmethod
    def send_bulk_push_notification(
        subscriptions: List[PushSubscription],
        title: str,
        message: str,
        action_url: Optional[str] = None
    ) -> Dict[str, int]:
        """Send push notification to multiple subscriptions"""
        try:
            success_count = 0
            failure_count = 0
            
            for subscription in subscriptions:
                if PushService.send_push_notification(
                    subscription, title, message, action_url
                ):
                    success_count += 1
                else:
                    failure_count += 1
            
            logger.info(f"Bulk push notification sent: {success_count} success, {failure_count} failures")
            
            return {
                "success_count": success_count,
                "failure_count": failure_count,
                "total_count": len(subscriptions)
            }
            
        except Exception as e:
            logger.error(f"Error sending bulk push notification: {str(e)}")
            return {
                "success_count": 0,
                "failure_count": len(subscriptions),
                "total_count": len(subscriptions)
            }

    @staticmethod
    def cleanup_inactive_subscriptions(db: Session, days_inactive: int = 30) -> int:
        """Clean up inactive push subscriptions"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
            
            inactive_subscriptions = db.query(PushSubscription).filter(
                PushSubscription.last_used < cutoff_date
            ).all()
            
            count = len(inactive_subscriptions)
            
            for subscription in inactive_subscriptions:
                subscription.is_active = False
            
            db.commit()
            
            logger.info(f"Cleaned up {count} inactive push subscriptions")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up inactive subscriptions: {str(e)}")
            db.rollback()
            return 0

    @staticmethod
    def get_push_statistics(db: Session) -> Dict[str, Any]:
        """Get push notification statistics"""
        try:
            total_subscriptions = db.query(PushSubscription).count()
            active_subscriptions = db.query(PushSubscription).filter(
                PushSubscription.is_active == True
            ).count()
            
            # Get subscriptions by device/browser
            device_stats = db.query(
                PushSubscription.device_name,
                db.func.count(PushSubscription.id).label('count')
            ).filter(
                PushSubscription.is_active == True
            ).group_by(PushSubscription.device_name).all()
            
            return {
                "total_subscriptions": total_subscriptions,
                "active_subscriptions": active_subscriptions,
                "inactive_subscriptions": total_subscriptions - active_subscriptions,
                "device_breakdown": [
                    {"device": device or "Unknown", "count": count}
                    for device, count in device_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting push statistics: {str(e)}")
            return {
                "total_subscriptions": 0,
                "active_subscriptions": 0,
                "inactive_subscriptions": 0,
                "device_breakdown": []
            }
