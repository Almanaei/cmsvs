"""
Message service for handling user-to-user messaging functionality
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime

from app.models.message import Message, Conversation
from app.models.user import User, UserRole


class MessageService:
    """Service class for message operations"""

    @staticmethod
    def send_message(
        db: Session,
        sender_id: int,
        recipient_id: int,
        subject: str,
        content: str
    ) -> Message:
        """Send a new message"""
        # Validate users exist
        sender = db.query(User).filter(User.id == sender_id).first()
        recipient = db.query(User).filter(User.id == recipient_id).first()
        
        if not sender or not recipient:
            raise ValueError("Sender or recipient not found")
        
        if not sender.is_active or not recipient.is_active:
            raise ValueError("Sender or recipient is not active")
        
        # Create message
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            subject=subject.strip(),
            content=content.strip()
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # Update or create conversation
        MessageService._update_conversation(db, sender_id, recipient_id, message.id)
        
        return message

    @staticmethod
    def get_user_inbox(
        db: Session,
        user_id: int,
        page: int = 1,
        per_page: int = 20,
        include_read: bool = True
    ) -> Dict[str, Any]:
        """Get user's inbox messages"""
        query = db.query(Message).filter(
            Message.recipient_id == user_id,
            Message.is_deleted_by_recipient == False
        )
        
        if not include_read:
            query = query.filter(Message.is_read == False)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        messages = query.order_by(desc(Message.created_at)).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            "messages": [msg.to_dict(user_id) for msg in messages],
            "total_count": total_count,
            "current_page": page,
            "total_pages": total_pages,
            "per_page": per_page,
            "unread_count": MessageService.get_unread_count(db, user_id)
        }

    @staticmethod
    def get_user_sent_messages(
        db: Session,
        user_id: int,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """Get user's sent messages"""
        query = db.query(Message).filter(
            Message.sender_id == user_id,
            Message.is_deleted_by_sender == False
        )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        messages = query.order_by(desc(Message.created_at)).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            "messages": [msg.to_dict(user_id) for msg in messages],
            "total_count": total_count,
            "current_page": page,
            "total_pages": total_pages,
            "per_page": per_page
        }

    @staticmethod
    def get_message_by_id(db: Session, message_id: int, user_id: int) -> Optional[Message]:
        """Get a specific message if user has access"""
        message = db.query(Message).filter(Message.id == message_id).first()
        
        if not message or not message.can_view(user_id):
            return None
        
        return message

    @staticmethod
    def mark_message_as_read(db: Session, message_id: int, user_id: int) -> bool:
        """Mark message as read"""
        message = db.query(Message).filter(
            Message.id == message_id,
            Message.recipient_id == user_id,
            Message.is_deleted_by_recipient == False
        ).first()
        
        if not message:
            return False
        
        message.mark_as_read()
        db.commit()
        return True

    @staticmethod
    def delete_message(db: Session, message_id: int, user_id: int) -> bool:
        """Delete message for user"""
        message = db.query(Message).filter(Message.id == message_id).first()
        
        if not message or not message.can_view(user_id):
            return False
        
        message.delete_for_user(user_id)
        db.commit()
        return True

    @staticmethod
    def get_unread_count(db: Session, user_id: int) -> int:
        """Get count of unread messages for user"""
        return db.query(Message).filter(
            Message.recipient_id == user_id,
            Message.is_read == False,
            Message.is_deleted_by_recipient == False
        ).count()

    @staticmethod
    def get_user_conversations(
        db: Session,
        user_id: int,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """Get user's conversations"""
        query = db.query(Conversation).filter(
            or_(
                Conversation.participant_1_id == user_id,
                Conversation.participant_2_id == user_id
            )
        )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        conversations = query.order_by(desc(Conversation.updated_at)).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            "conversations": [conv.to_dict(user_id) for conv in conversations],
            "total_count": total_count,
            "current_page": page,
            "total_pages": total_pages,
            "per_page": per_page
        }

    @staticmethod
    def get_conversation_messages(
        db: Session,
        conversation_id: int,
        user_id: int,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """Get messages in a conversation"""
        # Verify user is participant
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation or not conversation.has_participant(user_id):
            return {"messages": [], "total_count": 0, "current_page": 1, "total_pages": 0}
        
        # Get messages between the two participants
        other_participant = conversation.get_other_participant(user_id)
        
        query = db.query(Message).filter(
            or_(
                and_(
                    Message.sender_id == user_id,
                    Message.recipient_id == other_participant.id,
                    Message.is_deleted_by_sender == False
                ),
                and_(
                    Message.sender_id == other_participant.id,
                    Message.recipient_id == user_id,
                    Message.is_deleted_by_recipient == False
                )
            )
        )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination (newest first)
        messages = query.order_by(desc(Message.created_at)).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        # Reverse to show oldest first in conversation view
        messages.reverse()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            "messages": [msg.to_dict(user_id) for msg in messages],
            "conversation": conversation.to_dict(user_id),
            "total_count": total_count,
            "current_page": page,
            "total_pages": total_pages,
            "per_page": per_page
        }

    @staticmethod
    def _update_conversation(db: Session, user1_id: int, user2_id: int, message_id: int):
        """Update or create conversation between two users"""
        # Find existing conversation
        conversation = db.query(Conversation).filter(
            or_(
                and_(
                    Conversation.participant_1_id == user1_id,
                    Conversation.participant_2_id == user2_id
                ),
                and_(
                    Conversation.participant_1_id == user2_id,
                    Conversation.participant_2_id == user1_id
                )
            )
        ).first()
        
        if conversation:
            # Update existing conversation
            conversation.last_message_id = message_id
            conversation.updated_at = datetime.utcnow()
        else:
            # Create new conversation
            conversation = Conversation(
                participant_1_id=min(user1_id, user2_id),  # Consistent ordering
                participant_2_id=max(user1_id, user2_id),
                last_message_id=message_id
            )
            db.add(conversation)
        
        db.commit()
        return conversation

    @staticmethod
    def get_available_recipients(db: Session, current_user_id: int) -> List[Dict[str, Any]]:
        """Get list of users that can receive messages"""
        users = db.query(User).filter(
            User.id != current_user_id,
            User.is_active == True
        ).order_by(User.full_name).all()
        
        return [
            {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
                "role": user.role.value
            }
            for user in users
        ]
