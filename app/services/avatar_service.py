import os
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException
from PIL import Image
import io
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user_avatar import UserAvatar


class AvatarService:
    """Service for handling user avatar uploads and management"""
    
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    AVATAR_SIZE = (200, 200)  # Standard avatar size
    AVATAR_DIRECTORY = "avatars"
    
    @staticmethod
    def _ensure_avatar_directory():
        """Ensure avatar directory exists"""
        avatar_dir = os.path.join(settings.upload_directory, AvatarService.AVATAR_DIRECTORY)
        os.makedirs(avatar_dir, exist_ok=True)
        return avatar_dir
    
    @staticmethod
    def _is_valid_image(file: UploadFile) -> bool:
        """Validate if uploaded file is a valid image"""
        if not file.filename:
            return False
            
        # Check file extension
        extension = file.filename.lower().split('.')[-1]
        if extension not in AvatarService.ALLOWED_EXTENSIONS:
            return False
            
        # Check file size
        if file.size and file.size > AvatarService.MAX_FILE_SIZE:
            return False
            
        return True
    
    @staticmethod
    async def _process_image(file: UploadFile) -> bytes:
        """Process and resize image"""
        try:
            # Read file content
            content = await file.read()
            
            # Open image with PIL
            image = Image.open(io.BytesIO(content))
            
            # Convert to RGB if necessary (for PNG with transparency)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize image to standard avatar size
            image = image.resize(AvatarService.AVATAR_SIZE, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
    
    @staticmethod
    async def upload_avatar(file: UploadFile, user_id: int, db: Session) -> str:
        """Upload and process user avatar"""
        # Validate file
        if not AvatarService._is_valid_image(file):
            raise HTTPException(
                status_code=400, 
                detail="Invalid image file. Allowed formats: JPG, JPEG, PNG, GIF, WEBP. Max size: 5MB"
            )
        
        # Ensure directory exists
        avatar_dir = AvatarService._ensure_avatar_directory()
        
        # Generate unique filename
        file_extension = 'jpg'  # Always save as JPEG after processing
        filename = f"user_{user_id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(avatar_dir, filename)
        
        # Process image
        processed_image = await AvatarService._process_image(file)
        
        # Save processed image
        with open(file_path, 'wb') as f:
            f.write(processed_image)

        # Save to database (use forward slashes for web URLs)
        relative_path = f"{AvatarService.AVATAR_DIRECTORY}/{filename}"

        # Check if user already has an avatar record
        existing_avatar = db.query(UserAvatar).filter(UserAvatar.user_id == user_id).first()

        if existing_avatar:
            # Delete old file if it exists
            old_file_path = os.path.join(settings.upload_directory, existing_avatar.avatar_url)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

            # Update existing record
            existing_avatar.avatar_url = relative_path
        else:
            # Create new record
            new_avatar = UserAvatar(user_id=user_id, avatar_url=relative_path)
            db.add(new_avatar)

        db.commit()

        # Return relative path for database storage
        return relative_path
    
    @staticmethod
    def delete_avatar(user_id: int, db: Session) -> bool:
        """Delete avatar file and database record"""
        try:
            # Get avatar record
            avatar_record = db.query(UserAvatar).filter(UserAvatar.user_id == user_id).first()

            if avatar_record:
                # Delete file if it exists
                if avatar_record.avatar_url and not avatar_record.avatar_url.startswith('http'):
                    file_path = os.path.join(settings.upload_directory, avatar_record.avatar_url)
                    if os.path.exists(file_path):
                        os.remove(file_path)

                # Delete database record
                db.delete(avatar_record)
                db.commit()

            return True
        except Exception:
            return False
    
    @staticmethod
    def get_avatar_url(user_id: int, full_name: str, db: Session) -> str:
        """Get avatar URL from database or generate default avatar"""
        # Try to get avatar from database
        avatar_record = db.query(UserAvatar).filter(UserAvatar.user_id == user_id).first()

        if avatar_record and avatar_record.avatar_url:
            # Check if it's already a full URL (external service)
            if avatar_record.avatar_url.startswith('http'):
                return avatar_record.avatar_url
            # Check if local file exists (convert path separators for file system check)
            file_path = os.path.join(settings.upload_directory, avatar_record.avatar_url.replace('/', os.sep))
            if os.path.exists(file_path):
                # Return URL with forward slashes for web
                return f"/static/uploads/{avatar_record.avatar_url}"

        # Generate default avatar based on user initials
        return AvatarService.generate_default_avatar_url(user_id, full_name)
    
    @staticmethod
    def generate_default_avatar_url(user_id: int, full_name: str) -> str:
        """Generate default avatar URL using external service"""
        # Extract initials
        names = full_name.strip().split()
        if len(names) >= 2:
            initials = f"{names[0][0]}{names[1][0]}"
        elif len(names) == 1:
            initials = names[0][:2]
        else:
            initials = "U"
        
        # Use UI Avatars service for default avatars
        # Colors based on user ID for consistency
        colors = ['3B82F6', '10B981', 'F59E0B', 'EF4444', '8B5CF6', '06B6D4', 'F97316', 'EC4899']
        color = colors[user_id % len(colors)]
        
        return f"https://ui-avatars.com/api/?name={initials}&size=200&background={color}&color=fff&bold=true"
    
    @staticmethod
    def get_file_path(avatar_url: str) -> str:
        """Get full file path for avatar"""
        return os.path.join(settings.upload_directory, avatar_url)
