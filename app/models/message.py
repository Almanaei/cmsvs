"""
Message model for user-to-user messaging system
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Message(Base):
    """Message model for user-to-user communication"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    is_deleted_by_sender = Column(Boolean, default=False, nullable=False)
    is_deleted_by_recipient = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")

    def __repr__(self):
        return f"<Message(id={self.id}, sender_id={self.sender_id}, recipient_id={self.recipient_id}, subject='{self.subject[:30]}...')>"

    @property
    def is_deleted(self):
        """Check if message is deleted by both sender and recipient"""
        return self.is_deleted_by_sender and self.is_deleted_by_recipient

    def delete_for_user(self, user_id: int):
        """Mark message as deleted for specific user"""
        if user_id == self.sender_id:
            self.is_deleted_by_sender = True
        elif user_id == self.recipient_id:
            self.is_deleted_by_recipient = True

    def can_view(self, user_id: int) -> bool:
        """Check if user can view this message"""
        if user_id == self.sender_id:
            return not self.is_deleted_by_sender
        elif user_id == self.recipient_id:
            return not self.is_deleted_by_recipient
        return False

    def mark_as_read(self):
        """Mark message as read"""
        self.is_read = True

    def to_dict(self, current_user_id: int = None):
        """Convert message to dictionary for API responses"""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "sender_name": self.sender.full_name if self.sender else "Unknown",
            "recipient_name": self.recipient.full_name if self.recipient else "Unknown",
            "subject": self.subject,
            "content": self.content,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_sent_by_me": current_user_id == self.sender_id if current_user_id else False,
            "is_received_by_me": current_user_id == self.recipient_id if current_user_id else False
        }


class Conversation(Base):
    """Conversation model for message threading"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    participant_1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    participant_2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    last_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    participant_1 = relationship("User", foreign_keys=[participant_1_id])
    participant_2 = relationship("User", foreign_keys=[participant_2_id])
    last_message = relationship("Message", foreign_keys=[last_message_id])

    def __repr__(self):
        return f"<Conversation(id={self.id}, participant_1_id={self.participant_1_id}, participant_2_id={self.participant_2_id})>"

    def get_other_participant(self, user_id: int):
        """Get the other participant in the conversation"""
        if user_id == self.participant_1_id:
            return self.participant_2
        elif user_id == self.participant_2_id:
            return self.participant_1
        return None

    def has_participant(self, user_id: int) -> bool:
        """Check if user is a participant in this conversation"""
        return user_id in [self.participant_1_id, self.participant_2_id]

    def to_dict(self, current_user_id: int = None):
        """Convert conversation to dictionary for API responses"""
        other_participant = self.get_other_participant(current_user_id)
        return {
            "id": self.id,
            "other_participant": {
                "id": other_participant.id if other_participant else None,
                "name": other_participant.full_name if other_participant else "Unknown",
                "username": other_participant.username if other_participant else "unknown"
            },
            "last_message": self.last_message.to_dict(current_user_id) if self.last_message else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
