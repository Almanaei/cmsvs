import os
import uuid
import mimetypes
import threading
import time
import hashlib
import magic
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import UploadFile, HTTPException
from app.config import settings


class FileHandler:
    """Handle file upload operations with thread-safe concurrency support - Production Ready"""

    # Thread-safe locks for file operations
    _file_operation_lock = threading.Lock()
    _directory_creation_lock = threading.Lock()
    _filename_generation_lock = threading.Lock()

    # Production logging
    _logger = logging.getLogger(__name__)
    
    @staticmethod
    async def validate_file(file: UploadFile) -> Dict[str, Any]:
        """Enhanced file validation with security checks"""
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "file_info": {}
        }

        try:
            # Check if file has a name
            if not file.filename:
                validation_result["errors"].append("File must have a filename")
                return validation_result

            # Get file extension
            file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
            if not file_ext:
                validation_result["errors"].append("File must have an extension")
                return validation_result

            # Check file extension against allowed types
            if file_ext not in settings.allowed_file_types_list:
                validation_result["errors"].append(
                    f"File type '{file_ext}' not allowed. Allowed types: {', '.join(settings.allowed_file_types_list)}"
                )
                return validation_result

            # Read file content for validation
            await file.seek(0)  # Ensure we start from the beginning
            content = await file.read()
            file_size = len(content)

            # Reset file pointer for later use
            await file.seek(0)

            # Check file size
            if file_size == 0:
                validation_result["errors"].append("File is empty")
                return validation_result

            if file_size > settings.max_file_size:
                validation_result["errors"].append(
                    f"File size ({file_size} bytes) exceeds maximum allowed size ({settings.max_file_size} bytes)"
                )
                return validation_result

            # MIME type validation using python-magic (with fallback)
            try:
                import magic
                mime_type = magic.from_buffer(content, mime=True)
                file_type_from_content = magic.from_buffer(content)
            except (ImportError, Exception):
                # Fallback to mimetypes if python-magic fails or not available
                mime_type, _ = mimetypes.guess_type(file.filename)
                file_type_from_content = f"File type detection unavailable (install python-magic for better detection)"

            # Validate MIME type matches extension
            expected_mimes = FileHandler._get_expected_mime_types(file_ext)
            if mime_type and expected_mimes and mime_type not in expected_mimes:
                validation_result["warnings"].append(
                    f"File content type ({mime_type}) doesn't match extension ({file_ext})"
                )

            # Security checks
            security_issues = FileHandler._security_scan(content, file.filename)
            if security_issues:
                validation_result["errors"].extend(security_issues)
                return validation_result

            # Generate file hash for duplicate detection
            file_hash = hashlib.sha256(content).hexdigest()

            validation_result.update({
                "valid": True,
                "file_info": {
                    "filename": file.filename,
                    "size": file_size,
                    "extension": file_ext,
                    "mime_type": mime_type,
                    "file_type": file_type_from_content,
                    "hash": file_hash
                }
            })

            return validation_result

        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            return validation_result
    
    @staticmethod
    def _get_expected_mime_types(file_ext: str) -> List[str]:
        """Get expected MIME types for file extension"""
        mime_map = {
            'pdf': ['application/pdf'],
            'doc': ['application/msword'],
            'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'txt': ['text/plain'],
            'jpg': ['image/jpeg'],
            'jpeg': ['image/jpeg'],
            'png': ['image/png'],
            'gif': ['image/gif']
        }
        return mime_map.get(file_ext.lower(), [])

    @staticmethod
    def _security_scan(content: bytes, filename: str) -> List[str]:
        """Basic security scanning for malicious content"""
        issues = []

        # Check for suspicious file signatures
        suspicious_signatures = [
            b'\x4d\x5a',  # PE executable
            b'\x7f\x45\x4c\x46',  # ELF executable
            b'\xca\xfe\xba\xbe',  # Java class file
            b'\xfe\xed\xfa\xce',  # Mach-O executable
        ]

        for sig in suspicious_signatures:
            if content.startswith(sig):
                issues.append("File appears to be an executable")
                break

        # Check for script content in non-script files
        if filename.lower().endswith(('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif')):
            script_patterns = [b'<script', b'javascript:', b'vbscript:', b'<?php']
            for pattern in script_patterns:
                if pattern in content.lower():
                    issues.append("File contains potentially malicious script content")
                    break

        # Check file size vs content (zip bombs, etc.)
        if len(content) > settings.max_file_size * 2:  # Should never happen due to earlier check
            issues.append("File size inconsistency detected")

        return issues

    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """Generate thread-safe unique filename while preserving extension"""
        with FileHandler._filename_generation_lock:
            if not original_filename:
                return f"{uuid.uuid4().hex}.tmp"

            name, ext = os.path.splitext(original_filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Include microseconds for uniqueness
            unique_id = uuid.uuid4().hex[:12]

            # Add small delay to ensure uniqueness even in high-concurrency scenarios
            time.sleep(0.001)  # 1ms delay

            return f"{timestamp}_{unique_id}{ext}"
    
    @staticmethod
    def get_file_info(file: UploadFile) -> dict:
        """Get file information"""
        mime_type, _ = mimetypes.guess_type(file.filename or "")
        file_ext = ""
        
        if file.filename:
            file_ext = file.filename.split('.')[-1].lower()
        
        return {
            "original_filename": file.filename or "unknown",
            "file_type": file_ext,
            "mime_type": mime_type or "application/octet-stream",
            "content_type": file.content_type or mime_type or "application/octet-stream"
        }
    
    @staticmethod
    async def save_file(file: UploadFile, request_id: int, custom_filename: Optional[str] = None) -> dict:
        """Save uploaded file to disk with enhanced validation and security - Production Ready"""
        FileHandler._logger.info(f"Starting file save: original='{file.filename}', request_id={request_id}, custom_filename='{custom_filename}'")

        try:
            # Enhanced file validation
            validation_result = await FileHandler.validate_file(file)

            if not validation_result["valid"]:
                error_msg = "; ".join(validation_result["errors"])
                FileHandler._logger.error(f"File validation failed for '{file.filename}': {error_msg}")
                raise HTTPException(status_code=400, detail=f"File validation failed: {error_msg}")

            file_info = validation_result["file_info"]
            FileHandler._logger.info(f"File validation passed: size={file_info['size']}, type={file_info['extension']}")

            # Use custom filename if provided, otherwise generate unique filename
            if custom_filename:
                stored_filename = custom_filename
                FileHandler._logger.info(f"Using custom filename: '{stored_filename}'")
            else:
                stored_filename = FileHandler.generate_unique_filename(file.filename)
                FileHandler._logger.info(f"Generated filename: '{stored_filename}'")

            # Thread-safe directory creation
            request_dir = os.path.join(settings.upload_directory, f"request_{request_id}")
            with FileHandler._directory_creation_lock:
                os.makedirs(request_dir, exist_ok=True)

            # Full file path
            file_path = os.path.join(request_dir, stored_filename)

            # Ensure filename is unique even if generated simultaneously
            original_file_path = file_path
            original_stored_filename = stored_filename
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(original_stored_filename)
                stored_filename = f"{name}_copy_{counter}{ext}"
                file_path = os.path.join(request_dir, stored_filename)
                counter += 1

            # Atomic file save operation
            await file.seek(0)  # Ensure we start from the beginning
            content = await file.read()

            # Verify file size hasn't changed
            if len(content) != file_info["size"]:
                raise HTTPException(
                    status_code=400,
                    detail="File size changed during upload"
                )

            # Use temporary file for atomic write operation
            temp_file_path = f"{file_path}.tmp"

            with FileHandler._file_operation_lock:
                # Write to temporary file first
                with open(temp_file_path, "wb") as f:
                    f.write(content)

                # Verify written file
                if os.path.getsize(temp_file_path) != len(content):
                    raise Exception("File write verification failed")

                # Atomically move temporary file to final location
                if os.path.exists(temp_file_path):
                    os.rename(temp_file_path, file_path)

            FileHandler._logger.info(f"File saved successfully: '{stored_filename}' at '{file_path}'")

            return {
                "original_filename": file_info["filename"],
                "stored_filename": stored_filename,
                "file_path": file_path,
                "file_size": file_info["size"],
                "file_type": file_info["extension"],
                "mime_type": file_info["mime_type"],
                "file_hash": file_info["hash"],
                "warnings": validation_result.get("warnings", [])
            }

        except Exception as e:
            # Clean up files if save failed
            FileHandler._logger.error(f"File save failed for '{file.filename}': {str(e)}")
            temp_file_path = f"{file_path}.tmp" if 'file_path' in locals() else None
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}"
            )
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete file from disk"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    @staticmethod
    async def validate_multiple_files(files: List[UploadFile], max_files: Optional[int] = None) -> Dict[str, Any]:
        """Validate multiple files with comprehensive checks"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "file_results": [],
            "total_size": 0,
            "duplicate_hashes": []
        }

        # Check file count
        if max_files and len(files) > max_files:
            validation_result["errors"].append(f"Too many files. Maximum allowed: {max_files}")
            validation_result["valid"] = False
            return validation_result

        # Track file hashes for duplicate detection
        file_hashes = {}
        total_size = 0

        for i, file in enumerate(files):
            if not file.filename:  # Skip empty file inputs
                continue

            file_validation = await FileHandler.validate_file(file)
            validation_result["file_results"].append({
                "index": i,
                "filename": file.filename,
                "validation": file_validation
            })

            if not file_validation["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend([
                    f"File '{file.filename}': {error}" for error in file_validation["errors"]
                ])
            else:
                file_info = file_validation["file_info"]
                total_size += file_info["size"]

                # Check for duplicates
                file_hash = file_info["hash"]
                if file_hash in file_hashes:
                    validation_result["warnings"].append(
                        f"Duplicate file detected: '{file.filename}' is identical to '{file_hashes[file_hash]}'"
                    )
                    validation_result["duplicate_hashes"].append(file_hash)
                else:
                    file_hashes[file_hash] = file.filename

                # Add warnings from individual file validation
                validation_result["warnings"].extend([
                    f"File '{file.filename}': {warning}" for warning in file_validation.get("warnings", [])
                ])

        validation_result["total_size"] = total_size

        # Check total size limit (10x single file limit)
        max_total_size = settings.max_file_size * 10
        if total_size > max_total_size:
            validation_result["errors"].append(
                f"Total file size ({total_size} bytes) exceeds maximum allowed ({max_total_size} bytes)"
            )
            validation_result["valid"] = False

        return validation_result

    @staticmethod
    def validate_file_count(files: List[UploadFile]) -> bool:
        """Validate number of files (unlimited) - kept for backward compatibility"""
        return True
