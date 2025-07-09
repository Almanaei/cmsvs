from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
from datetime import datetime


class AchievementType(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MILESTONE = "milestone"
    STREAK = "streak"
    SPECIAL = "special"


class CompetitionStatus(enum.Enum):
    ACTIVE = "active"
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Achievement(Base):
    """Achievement definitions and templates"""
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    achievement_type = Column(SQLEnum(AchievementType), nullable=False)
    target_value = Column(Integer, nullable=False)  # Target number (e.g., 10 for daily)
    points = Column(Integer, default=0)  # Points awarded for this achievement
    badge_icon = Column(String(100), nullable=True)  # Icon class or emoji
    badge_color = Column(String(50), default="blue")  # Badge color theme
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")

    def __repr__(self):
        return f"<Achievement(name='{self.name}', type='{self.achievement_type}')>"


class UserAchievement(Base):
    """User achievement progress and completions"""
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    current_progress = Column(Integer, default=0)  # Current progress towards target
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    points_earned = Column(Integer, default=0)
    period_start = Column(DateTime(timezone=True), nullable=True)  # For time-based achievements
    period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

    def __repr__(self):
        return f"<UserAchievement(user_id={self.user_id}, achievement_id={self.achievement_id}, progress={self.current_progress})>"


class Competition(Base):
    """Competition events and challenges"""
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    competition_type = Column(SQLEnum(AchievementType), nullable=False)  # daily, weekly, monthly
    target_value = Column(Integer, nullable=False)  # Target to achieve
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(SQLEnum(CompetitionStatus), default=CompetitionStatus.UPCOMING)
    
    # Rewards
    first_place_points = Column(Integer, default=100)
    second_place_points = Column(Integer, default=75)
    third_place_points = Column(Integer, default=50)
    participation_points = Column(Integer, default=10)
    
    # Competition settings
    max_participants = Column(Integer, nullable=True)  # Null = unlimited
    is_public = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship("CompetitionParticipant", back_populates="competition")

    def __repr__(self):
        return f"<Competition(name='{self.name}', type='{self.competition_type}', status='{self.status}')>"


class CompetitionParticipant(Base):
    """Competition participants and their progress"""
    __tablename__ = "competition_participants"

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_progress = Column(Integer, default=0)
    final_score = Column(Integer, default=0)
    rank = Column(Integer, nullable=True)  # Final ranking
    points_earned = Column(Integer, default=0)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    competition = relationship("Competition", back_populates="participants")
    user = relationship("User")

    def __repr__(self):
        return f"<CompetitionParticipant(competition_id={self.competition_id}, user_id={self.user_id}, progress={self.current_progress})>"


class UserStats(Base):
    """User statistics and leaderboard data"""
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Achievement points
    total_points = Column(Integer, default=0)
    daily_points = Column(Integer, default=0)
    weekly_points = Column(Integer, default=0)
    monthly_points = Column(Integer, default=0)
    
    # Streaks
    current_daily_streak = Column(Integer, default=0)
    longest_daily_streak = Column(Integer, default=0)
    current_weekly_streak = Column(Integer, default=0)
    longest_weekly_streak = Column(Integer, default=0)
    
    # Achievements
    total_achievements = Column(Integer, default=0)
    daily_achievements = Column(Integer, default=0)
    weekly_achievements = Column(Integer, default=0)
    monthly_achievements = Column(Integer, default=0)
    
    # Rankings
    global_rank = Column(Integer, nullable=True)
    daily_rank = Column(Integer, nullable=True)
    weekly_rank = Column(Integer, nullable=True)
    monthly_rank = Column(Integer, nullable=True)
    
    # Last activity tracking
    last_daily_completion = Column(DateTime(timezone=True), nullable=True)
    last_weekly_completion = Column(DateTime(timezone=True), nullable=True)
    last_monthly_completion = Column(DateTime(timezone=True), nullable=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="stats")

    def __repr__(self):
        return f"<UserStats(user_id={self.user_id}, total_points={self.total_points}, global_rank={self.global_rank})>"
