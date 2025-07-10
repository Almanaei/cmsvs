from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class NotificationType(enum.Enum):
    REQUEST_STATUS_CHANGED = "request_status_changed"
    REQUEST_CREATED = "request_created"
    REQUEST_UPDATED = "request_updated"
    REQUEST_ARCHIVED = "request_archived"
    REQUEST_DELETED = "request_deleted"
    ADMIN_MESSAGE = "admin_message"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationPriority(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """Notification model for push notifications and in-app notifications"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)
    
    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    action_url = Column(String(500), nullable=True)  # URL to navigate when clicked
    
    # Related entities
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=True)
    related_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who made the change
    
    # Status tracking
    is_read = Column(Boolean, default=False, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)  # For push notifications
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data (JSON field for flexible data storage)
    extra_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    request = relationship("Request", back_populates="notifications")
    related_user = relationship("User", foreign_keys=[related_user_id])

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.type.value}', user_id={self.user_id})>"


class PushSubscription(Base):
    """Store push notification subscriptions for users"""
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Push subscription data
    endpoint = Column(String(500), nullable=False)
    p256dh_key = Column(String(255), nullable=False)
    auth_key = Column(String(255), nullable=False)
    
    # Device/browser info
    user_agent = Column(String(500), nullable=True)
    device_name = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="push_subscriptions")

    def __repr__(self):
        return f"<PushSubscription(id={self.id}, user_id={self.user_id}, device='{self.device_name}')>"


class NotificationPreference(Base):
    """User notification preferences"""
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # General preferences
    push_notifications_enabled = Column(Boolean, default=True, nullable=False)
    in_app_notifications_enabled = Column(Boolean, default=True, nullable=False)
    email_notifications_enabled = Column(Boolean, default=False, nullable=False)
    
    # Notification type preferences
    request_status_notifications = Column(Boolean, default=True, nullable=False)
    request_updates_notifications = Column(Boolean, default=True, nullable=False)
    admin_message_notifications = Column(Boolean, default=True, nullable=False)
    system_announcement_notifications = Column(Boolean, default=True, nullable=False)
    
    # Timing preferences
    quiet_hours_enabled = Column(Boolean, default=False, nullable=False)
    quiet_hours_start = Column(String(5), nullable=True)  # Format: "22:00"
    quiet_hours_end = Column(String(5), nullable=True)    # Format: "08:00"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="notification_preferences")

    def __repr__(self):
        return f"<NotificationPreference(user_id={self.user_id}, push_enabled={self.push_notifications_enabled})>"
