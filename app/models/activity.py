from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ActivityType(enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REQUEST_CREATED = "request_created"
    REQUEST_UPDATED = "request_updated"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_REJECTED = "request_rejected"
    FILE_UPLOADED = "file_uploaded"
    FILE_DELETED = "file_deleted"
    PROFILE_UPDATED = "profile_updated"
    AVATAR_UPLOADED = "avatar_uploaded"
    PASSWORD_CHANGED = "password_changed"
    DATA_EXPORTED = "data_exported"
    SYSTEM_UPDATE = "system_update"


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    activity_type = Column(Enum(ActivityType), nullable=False)
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)  # Additional details as JSON
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="activities")

    def __repr__(self):
        return f"<Activity(type='{self.activity_type}', user_id={self.user_id})>"
