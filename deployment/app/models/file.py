from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import os
import threading
import time
import logging
import re
from datetime import datetime
from typing import Optional, Tuple


class File(Base):
    __tablename__ = "files"

    # Thread-safe lock for filename generation
    _filename_lock = threading.Lock()

    # Production logging
    _logger = logging.getLogger(__name__)

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_category = Column(String(100), nullable=False, default="general")  # Category for file organization
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    request = relationship("Request", back_populates="files")

    def __repr__(self):
        return f"<File(original_filename='{self.original_filename}', stored_filename='{self.stored_filename}')>"

    @classmethod
    def validate_filename_components(cls, original_filename: str, category: str, field_id: Optional[str] = None) -> Tuple[bool, str]:
        """Validate filename components for production safety"""
        try:
            # Validate original filename
            if not original_filename or not original_filename.strip():
                return False, "Original filename cannot be empty"

            # Sanitize original filename
            original_filename = original_filename.strip()
            if len(original_filename) > 255:
                return False, "Original filename too long (max 255 characters)"

            # Check for dangerous characters
            dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
            if any(char in original_filename for char in dangerous_chars):
                return False, f"Original filename contains dangerous characters: {dangerous_chars}"

            # Validate category
            if not category or not category.strip():
                return False, "Category cannot be empty"

            category = category.strip()
            if not re.match(r'^[a-zA-Z0-9_]+$', category):
                return False, "Category must contain only alphanumeric characters and underscores"

            if len(category) > 50:
                return False, "Category too long (max 50 characters)"

            # Validate field_id if provided
            if field_id is not None:
                field_id = str(field_id).strip()
                if not re.match(r'^[a-zA-Z0-9_]+$', field_id):
                    return False, "Field ID must contain only alphanumeric characters and underscores"

                if len(field_id) > 20:
                    return False, "Field ID too long (max 20 characters)"

            return True, "Valid"

        except Exception as e:
            cls._logger.error(f"Error validating filename components: {str(e)}")
            return False, f"Validation error: {str(e)}"

    @classmethod
    def generate_unique_filename(cls, original_filename: str, category: str = "general", field_id: Optional[str] = None, request_number: Optional[str] = None) -> str:
        """Generate thread-safe unique filename based on category, request, date, and field ID - Production Ready"""
        with cls._filename_lock:
            try:
                # Production logging
                cls._logger.info(f"Generating filename for: original='{original_filename}', category='{category}', field_id='{field_id}', request='{request_number}'")

                # Validate inputs
                is_valid, error_msg = cls.validate_filename_components(original_filename, category, field_id)
                if not is_valid:
                    cls._logger.error(f"Filename validation failed: {error_msg}")
                    raise ValueError(f"Invalid filename components: {error_msg}")

                # Sanitize and extract extension
                name, ext = os.path.splitext(original_filename.strip())

                # Ensure extension is lowercase and safe
                ext = ext.lower()
                if not ext:
                    ext = '.tmp'  # Default extension for files without extension

                # Generate production-grade timestamp with microseconds
                now = datetime.now()
                timestamp = now.strftime("%Y%m%d_%H%M%S_%f")

                # Add small delay to ensure uniqueness in high-concurrency scenarios
                time.sleep(0.001)  # 1ms delay

                # Sanitize request number for filename use
                request_part = ""
                if request_number:
                    # Extract meaningful part from request number (e.g., REQ-20250614034524 -> 20250614034524)
                    request_clean = request_number.replace("REQ-", "").replace("-", "")
                    # Take last 8 characters to keep filename manageable
                    request_part = f"_{request_clean[-8:]}" if request_clean else ""

                # Create request-specific category-based filename
                if field_id:
                    generated_filename = f"{category}{request_part}_{timestamp}_{field_id}{ext}"
                else:
                    # Generate secure unique ID
                    unique_id = str(uuid.uuid4()).replace("-", "")[:8]
                    generated_filename = f"{category}{request_part}_{timestamp}_{unique_id}{ext}"

                # Final validation of generated filename
                if len(generated_filename) > 255:
                    cls._logger.error(f"Generated filename too long: {len(generated_filename)} characters")
                    # Truncate timestamp if needed
                    short_timestamp = now.strftime("%Y%m%d_%H%M%S")
                    if field_id:
                        generated_filename = f"{category}{request_part}_{short_timestamp}_{field_id}{ext}"
                    else:
                        unique_id = str(uuid.uuid4()).replace("-", "")[:6]
                        generated_filename = f"{category}{request_part}_{short_timestamp}_{unique_id}{ext}"

                cls._logger.info(f"Generated filename: '{generated_filename}'")
                return generated_filename

            except Exception as e:
                cls._logger.error(f"Error generating filename: {str(e)}")
                # Fallback to basic UUID-based filename
                fallback_filename = f"file_{str(uuid.uuid4()).replace('-', '')[:12]}.tmp"
                cls._logger.warning(f"Using fallback filename: '{fallback_filename}'")
                return fallback_filename

    @property
    def file_size_mb(self) -> float:
        """Get file size in MB"""
        if not self.file_size or self.file_size == 0:
            return 0.0
        return round(self.file_size / (1024 * 1024), 2)
