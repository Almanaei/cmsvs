from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(enum.Enum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"


class UserStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    # avatar_url = Column(String(500), nullable=True)  # Path to user's avatar image - Will be added later
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    approval_status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    requests = relationship("Request", back_populates="user")
    activities = relationship("Activity", back_populates="user")

    # Achievement relationships (defined as strings to avoid circular imports)
    achievements = relationship("UserAchievement", back_populates="user", lazy="dynamic")
    stats = relationship("UserStats", back_populates="user", uselist=False)
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.recipient_id", back_populates="recipient")

    # Notification relationships
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user")
    push_subscriptions = relationship("PushSubscription", back_populates="user")
    notification_preferences = relationship("NotificationPreference", back_populates="user", uselist=False)

    @property
    def avatar_url(self):
        """Get avatar URL from separate avatar table"""
        if hasattr(self, 'avatar_record') and self.avatar_record:
            return self.avatar_record.avatar_url
        return None

    @avatar_url.setter
    def avatar_url(self, value):
        """Set avatar URL in separate avatar table"""
        # This will be handled by the avatar service
        pass

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
