import os
import uuid
import mimetypes
import threading
import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import UploadFile
from app.config import settings


class FileHandler:
    """Handle file upload operations - Production Ready"""

    # Thread-safe locks for file operations
    _file_operation_lock = threading.Lock()
    _directory_creation_lock = threading.Lock()

    @staticmethod
    def _get_upload_dir():
        """Get upload directory from settings"""
        return getattr(settings, 'upload_directory', './uploads')

    @staticmethod
    def _get_max_file_size():
        """Get max file size from settings"""
        return getattr(settings, 'max_file_size', 10 * 1024 * 1024)  # 10MB default

    @staticmethod
    def _get_allowed_extensions():
        """Get allowed extensions from settings"""
        allowed_types = getattr(settings, 'allowed_file_types', 'pdf,doc,docx,jpg,jpeg,png,gif,txt')
        return set(ext.strip().lower() for ext in allowed_types.split(','))

    @staticmethod
    def _ensure_upload_directory(upload_dir: str):
        """Ensure upload directory exists with proper permissions"""
        with FileHandler._directory_creation_lock:
            try:
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir, mode=0o755, exist_ok=True)
                    logging.getLogger(__name__).info(f"Created upload directory: {upload_dir}")

                # Verify directory is writable
                if not os.access(upload_dir, os.W_OK):
                    raise Exception(f"Upload directory is not writable: {upload_dir}")

            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to create upload directory: {str(e)}")
                raise

    @staticmethod
    async def validate_file(file: UploadFile) -> Dict[str, Any]:
        """Comprehensive file validation with security checks"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "file_info": {
                "original_name": file.filename,
                "size": 0,
                "mime_type": None,
                "extension": None,
                "content_type": file.content_type
            }
        }

        try:
            # Read file content for validation
            content = await file.read()
            await file.seek(0)  # Reset file pointer

            file_size = len(content)
            validation_result["file_info"]["size"] = file_size

            # Basic filename validation
            if not file.filename or file.filename.strip() == "":
                validation_result["errors"].append("Filename is required")
                return validation_result

            # Check for dangerous filenames
            dangerous_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
            if any(pattern in file.filename for pattern in dangerous_patterns):
                validation_result["errors"].append("Filename contains invalid characters")
                return validation_result

            # Extract file extension
            file_extension = os.path.splitext(file.filename)[1].lower().lstrip('.')
            validation_result["file_info"]["extension"] = file_extension

            # Check file size
            max_file_size = FileHandler._get_max_file_size()
            if file_size > max_file_size:
                validation_result["errors"].append(f"File size ({file_size} bytes) exceeds maximum allowed size ({max_file_size} bytes)")
                return validation_result

            if file_size == 0:
                validation_result["errors"].append("File is empty")
                return validation_result

            # Check allowed extensions
            allowed_extensions = FileHandler._get_allowed_extensions()
            if allowed_extensions and file_extension not in allowed_extensions:
                validation_result["errors"].append(f"File type '{file_extension}' is not allowed. Allowed types: {', '.join(allowed_extensions)}")
                return validation_result

            # Determine MIME type
            mime_type = mimetypes.guess_type(file.filename)[0]
            validation_result["file_info"]["mime_type"] = mime_type

            # Additional security checks for content
            if file_extension in ['exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js']:
                validation_result["errors"].append("Executable files are not allowed")
                return validation_result

            # Check for suspicious content patterns (basic)
            try:
                content_str = content[:1024].decode('utf-8', errors='ignore').lower()
                suspicious_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
                if any(pattern in content_str for pattern in suspicious_patterns):
                    validation_result["warnings"].append("File contains potentially suspicious content")
            except:
                pass  # Skip content check if decoding fails

            # Mark as valid if no errors
            validation_result["valid"] = len(validation_result["errors"]) == 0

        except Exception as e:
            validation_result["errors"].append(f"File validation failed: {str(e)}")
            validation_result["valid"] = False

        return validation_result

    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """Generate a unique filename to prevent conflicts"""
        try:
            if not original_filename:
                return f"{uuid.uuid4().hex}.tmp"

            name, ext = os.path.splitext(original_filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            unique_id = uuid.uuid4().hex[:12]

            # Create filename: originalname_timestamp_uniqueid.ext
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name[:50]  # Limit length

            if not safe_name:
                safe_name = "file"

            unique_filename = f"{safe_name}_{timestamp}_{unique_id}{ext}"
            return unique_filename

        except Exception as e:
            logging.getLogger(__name__).error(f"Error generating unique filename: {str(e)}")
            return f"{uuid.uuid4().hex}{os.path.splitext(original_filename)[1] if original_filename else '.tmp'}"

    @staticmethod
    async def save_file(file: UploadFile, request_id: str, stored_filename: Optional[str] = None) -> Dict[str, Any]:
        """Save uploaded file with comprehensive error handling and security measures"""
        result = {
            "success": False,
            "file_path": None,
            "stored_filename": None,
            "original_filename": file.filename,
            "file_size": 0,
            "error": None,
            "warnings": []
        }

        try:
            # Validate file first
            validation = await FileHandler.validate_file(file)
            if not validation["valid"]:
                result["error"] = "; ".join(validation["errors"])
                return result

            # Add any warnings from validation
            if validation.get("warnings"):
                result["warnings"].extend(validation["warnings"])

            # Generate unique filename if not provided
            if not stored_filename:
                stored_filename = FileHandler.generate_unique_filename(file.filename)

            result["stored_filename"] = stored_filename

            # Get upload directory and ensure it exists
            upload_dir = FileHandler._get_upload_dir()
            FileHandler._ensure_upload_directory(upload_dir)

            # Create request-specific directory
            request_dir = os.path.join(upload_dir, str(request_id))
            FileHandler._ensure_upload_directory(request_dir)

            # Full file path
            file_path = os.path.join(request_dir, stored_filename)

            # Check if file already exists
            if os.path.exists(file_path):
                stored_filename = FileHandler.generate_unique_filename(file.filename)
                file_path = os.path.join(request_dir, stored_filename)
                result["stored_filename"] = stored_filename

            # Save file with thread safety
            with FileHandler._file_operation_lock:
                content = await file.read()

                # Write file atomically using temporary file
                temp_file_path = f"{file_path}.tmp"
                try:
                    with open(temp_file_path, "wb") as temp_file:
                        temp_file.write(content)
                        temp_file.flush()
                        os.fsync(temp_file.fileno())  # Force write to disk

                    # Atomic move
                    os.rename(temp_file_path, file_path)

                except Exception as e:
                    # Clean up temp file if something went wrong
                    if os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                        except:
                            pass
                    raise e

            # Verify file was saved correctly
            if not os.path.exists(file_path):
                raise Exception("File was not saved successfully")

            saved_size = os.path.getsize(file_path)
            if saved_size != len(content):
                raise Exception(f"File size mismatch: expected {len(content)}, got {saved_size}")

            # Set proper file permissions
            os.chmod(file_path, 0o644)

            result.update({
                "success": True,
                "file_path": file_path,
                "stored_filename": stored_filename,
                "file_size": saved_size
            })

            logging.getLogger(__name__).info(f"File saved successfully: {stored_filename} ({saved_size} bytes)")

        except Exception as e:
            error_msg = f"Failed to save file {file.filename}: {str(e)}"
            logging.getLogger(__name__).error(error_msg)
            result["error"] = error_msg

            # Clean up any partial files
            try:
                if result.get("file_path") and os.path.exists(result["file_path"]):
                    os.remove(result["file_path"])
            except:
                pass

        finally:
            # Reset file pointer
            try:
                await file.seek(0)
            except:
                pass

        return result

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete a file from the filesystem"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to delete file {file_path}: {str(e)}")
            return False

    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            if not os.path.exists(file_path):
                return {"exists": False, "error": "File not found"}

            stat_info = os.stat(file_path)
            file_info = {
                "exists": True,
                "size": stat_info.st_size,
                "created": datetime.fromtimestamp(stat_info.st_mtime),
                "modified": datetime.fromtimestamp(stat_info.st_mtime),
                "permissions": oct(stat_info.st_mode)[-3:],
                "extension": os.path.splitext(file_path)[1].lower().lstrip('.'),
                "mime_type": mimetypes.guess_type(file_path)[0]
            }

            return file_info

        except Exception as e:
            return {"exists": False, "error": str(e)}

    @staticmethod
    def validate_file_count(files: List[UploadFile]) -> bool:
        """Validate file count"""
        # Basic validation - could be extended to check max file count
        return len(files) > 0 if files else False

    @staticmethod
    def cleanup_temp_files(directory: str, max_age_hours: int = 24):
        """Clean up temporary files older than specified hours"""
        try:
            current_time = time.time()
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.tmp'):
                        file_path = os.path.join(root, file)
                        if os.path.getmtime(file_path) < current_time - (max_age_hours * 3600):
                            try:
                                os.remove(file_path)
                                logging.getLogger(__name__).info(f"Cleaned up temp file: {file_path}")
                            except Exception as e:
                                logging.getLogger(__name__).error(f"Failed to clean up temp file {file_path}: {str(e)}")
        except Exception as e:
            logging.getLogger(__name__).error(f"Error during temp file cleanup: {str(e)}")
