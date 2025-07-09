from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.user import User, UserRole, UserStatus
from app.models.activity import Activity, ActivityType
from app.utils.auth import get_password_hash, verify_password
from app.services.cache import cached, cache
from fastapi import HTTPException
import logging


logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations with caching support"""

    @staticmethod
    def create_user(
        db: Session,
        username: str,
        email: str,
        full_name: str,
        password: str,
        role: UserRole = UserRole.USER,
        avatar_url: Optional[str] = None
    ) -> User:
        """Create a new user"""
        # Check if username or email already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                raise HTTPException(status_code=400, detail="Username already registered")
            else:
                raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user with appropriate approval status
        hashed_password = get_password_hash(password)

        # Admin users are automatically approved and active
        if role == UserRole.ADMIN:
            is_active = True
            approval_status = UserStatus.APPROVED
        else:
            is_active = False  # Set inactive until approved
            approval_status = UserStatus.PENDING  # Set pending approval

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            avatar_url=avatar_url,
            role=role,
            is_active=is_active,
            approval_status=approval_status
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    @cached(ttl=300, key_prefix="user")
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID with caching"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            logger.debug(f"Retrieved user {user_id} from database")
        return user

    @staticmethod
    @cached(ttl=300, key_prefix="user")
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username with caching"""
        user = db.query(User).filter(User.username == username).first()
        if user:
            logger.debug(f"Retrieved user {username} from database")
        return user

    @staticmethod
    @cached(ttl=300, key_prefix="user")
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email with caching"""
        user = db.query(User).filter(User.email == email).first()
        if user:
            logger.debug(f"Retrieved user {email} from database")
        return user
    
    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def get_users_with_pagination(
        db: Session,
        limit: int = 20,
        skip: int = 0,
        search: Optional[str] = None,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        approval_filter: Optional[str] = None
    ) -> List[User]:
        """Get users with pagination and filtering"""
        query = db.query(User)

        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.full_name.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.username.ilike(search_term))
            )

        # Apply role filter
        if role_filter and role_filter != 'all':
            try:
                role_enum = UserRole(role_filter)
                query = query.filter(User.role == role_enum)
            except ValueError:
                pass  # Invalid role, ignore filter

        # Apply status filter
        if status_filter == 'active':
            query = query.filter(User.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(User.is_active == False)

        # Apply approval status filter
        if approval_filter:
            if approval_filter == 'pending':
                query = query.filter(User.approval_status == UserStatus.PENDING)
            elif approval_filter == 'approved':
                query = query.filter(User.approval_status == UserStatus.APPROVED)
            elif approval_filter == 'rejected':
                query = query.filter(User.approval_status == UserStatus.REJECTED)

        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())

        # Apply pagination
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_users_count(
        db: Session,
        search: Optional[str] = None,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        approval_filter: Optional[str] = None
    ) -> int:
        """Get total count of users with filtering"""
        query = db.query(User)

        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.full_name.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.username.ilike(search_term))
            )

        # Apply role filter
        if role_filter and role_filter != 'all':
            try:
                role_enum = UserRole(role_filter)
                query = query.filter(User.role == role_enum)
            except ValueError:
                pass  # Invalid role, ignore filter

        # Apply status filter
        if status_filter == 'active':
            query = query.filter(User.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(User.is_active == False)

        # Apply approval status filter
        if approval_filter:
            if approval_filter == 'pending':
                query = query.filter(User.approval_status == UserStatus.PENDING)
            elif approval_filter == 'approved':
                query = query.filter(User.approval_status == UserStatus.APPROVED)
            elif approval_filter == 'rejected':
                query = query.filter(User.approval_status == UserStatus.REJECTED)

        return query.count()
    
    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_active: Optional[bool] = None,
        role: Optional[UserRole] = None
    ) -> Optional[User]:
        """Update user information"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        if username is not None:
            # Check if username is already taken by another user
            existing = db.query(User).filter(
                User.username == username, User.id != user_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Username already taken")
            user.username = username
        
        if email is not None:
            # Check if email is already taken by another user
            existing = db.query(User).filter(
                User.email == email, User.id != user_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email already taken")
            user.email = email
        
        if full_name is not None:
            user.full_name = full_name

        if avatar_url is not None:
            user.avatar_url = avatar_url

        if is_active is not None:
            user.is_active = is_active

        if role is not None:
            user.role = role
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password with current password verification"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            return False

        user.hashed_password = get_password_hash(new_password)
        db.commit()

        return True

    @staticmethod
    def update_user_profile(
        db: Session,
        user_id: int,
        full_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Optional[User]:
        """Update user profile information"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        if full_name is not None:
            user.full_name = full_name
        if email is not None:
            user.email = email

        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def get_user_statistics(db: Session, user_id: int) -> dict:
        """Get user statistics"""
        from app.models.request import Request, RequestStatus

        # Get total requests
        total_requests = db.query(Request).filter(Request.user_id == user_id).count()

        # Get pending requests
        pending_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.PENDING
        ).count()

        # Get completed requests
        approved_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED
        ).count()

        # Get rejected requests
        rejected_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.REJECTED
        ).count()

        return {
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "completed_requests": approved_requests,
            "rejected_requests": rejected_requests
        }
    
    @staticmethod
    def get_user_activities(
        db: Session, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[Activity]:
        """Get user activities"""
        return db.query(Activity).filter(
            Activity.user_id == user_id
        ).order_by(desc(Activity.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def log_activity(
        db: Session,
        user_id: int,
        activity_type: ActivityType,
        description: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Activity:
        """Log user activity"""
        activity = Activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(activity)
        db.commit()
        db.refresh(activity)
        
        return activity

    @staticmethod
    def soft_delete_user(db: Session, user_id: int) -> bool:
        """Soft delete user by deactivating account"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        user.is_active = False
        db.commit()

        return True

    @staticmethod
    def restore_user(db: Session, user_id: int) -> bool:
        """Restore soft deleted user by reactivating account"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        user.is_active = True
        db.commit()

        return True

    @staticmethod
    def get_inactive_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get inactive (soft deleted) users"""
        return db.query(User).filter(
            User.is_active == False
        ).offset(skip).limit(limit).all()
