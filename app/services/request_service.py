from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, extract, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from app.models.request import Request, RequestStatus
from app.models.file import File
from app.models.user import User, UserRole
from app.utils.file_handler import FileHandler
from fastapi import UploadFile, HTTPException
from datetime import datetime, timedelta, date
import threading
import time
import logging


class RequestService:
    """Service for request operations with multi-user concurrency support - Production Ready"""

    # Thread-safe locks for critical operations
    _request_creation_lock = threading.Lock()
    _file_upload_lock = threading.Lock()

    # Production logging
    _logger = logging.getLogger(__name__)
    
    @staticmethod
    def create_request(
        db: Session,
        user_id: int,
        full_name: Optional[str] = None,
        personal_number: Optional[str] = None,
        phone_number: Optional[str] = None,
        building_name: Optional[str] = None,
        road_name: Optional[str] = None,
        building_number: Optional[str] = None,
        civil_defense_file_number: Optional[str] = None,
        building_permit_number: Optional[str] = None,
        licenses_section: bool = False,
        fire_equipment_section: bool = False,
        commercial_records_section: bool = False,
        engineering_offices_section: bool = False,
        hazardous_materials_section: bool = False,
        # Pre-generated request number (for file naming consistency)
        pre_generated_request_number: Optional[str] = None,
        # Legacy parameters for backward compatibility
        request_name: Optional[str] = None,
        request_title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Request:
        """Create a new request with civil defense form data or legacy data"""
        # Thread-safe request creation with retry logic
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                with RequestService._request_creation_lock:
                    # Use pre-generated request number if provided, otherwise generate new one
                    request_number = pre_generated_request_number or Request.generate_request_number()

                    request = Request(
                        request_number=request_number,
                        unique_code=Request.generate_unique_code(),
                        user_id=user_id,
                        # New civil defense fields
                        full_name=full_name,
                        personal_number=personal_number,
                        phone_number=phone_number,
                        building_name=building_name,
                        road_name=road_name,
                        building_number=building_number,
                        civil_defense_file_number=civil_defense_file_number,
                        building_permit_number=building_permit_number,
                        licenses_section=licenses_section,
                        fire_equipment_section=fire_equipment_section,
                        commercial_records_section=commercial_records_section,
                        engineering_offices_section=engineering_offices_section,
                        hazardous_materials_section=hazardous_materials_section,
                        # Legacy fields for backward compatibility
                        request_name=request_name,
                        request_title=request_title,
                        description=description
                    )

                    db.add(request)
                    db.commit()
                    db.refresh(request)

                    return request

            except (IntegrityError, OperationalError) as e:
                db.rollback()
                retry_count += 1

                if retry_count >= max_retries:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create request after {max_retries} attempts: {str(e)}"
                    )

                # Wait before retry with exponential backoff
                time.sleep(0.1 * (2 ** retry_count))

            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create request: {str(e)}"
                )
    
    @staticmethod
    def get_request_by_id(db: Session, request_id: int) -> Optional[Request]:
        """Get request by ID"""
        return db.query(Request).filter(Request.id == request_id).first()
    
    @staticmethod
    def get_request_by_number(db: Session, request_number: str) -> Optional[Request]:
        """Get request by request number"""
        return db.query(Request).filter(Request.request_number == request_number).first()

    @staticmethod
    def get_request_by_unique_code(db: Session, unique_code: str) -> Optional[Request]:
        """Get request by unique code"""
        return db.query(Request).filter(Request.unique_code == unique_code).first()

    @staticmethod
    def search_requests(
        db: Session,
        search_query: str,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Request]:
        """Search requests by various fields including unique code"""
        search_term = f"%{search_query}%"
        query = db.query(Request).filter(
            or_(
                Request.request_number.ilike(search_term),
                Request.unique_code.ilike(search_term),
                Request.request_title.ilike(search_term),
                Request.full_name.ilike(search_term),
                Request.personal_number.ilike(search_term),
                Request.phone_number.ilike(search_term),
                Request.building_permit_number.ilike(search_term)
            )
        )

        # Filter by user if specified
        if user_id:
            query = query.filter(Request.user_id == user_id)

        # Only show non-archived requests
        query = query.filter(Request.is_archived == False)

        return query.order_by(desc(Request.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_user_requests(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
        search_query: Optional[str] = None
    ) -> List[Request]:
        """Get requests for a specific user with optional search"""
        query = db.query(Request).filter(Request.user_id == user_id)

        # Search functionality
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Request.request_number.ilike(search_term),
                    Request.unique_code.ilike(search_term),
                    Request.request_title.ilike(search_term),
                    Request.full_name.ilike(search_term),
                    Request.personal_number.ilike(search_term),
                    Request.phone_number.ilike(search_term),
                    Request.building_permit_number.ilike(search_term)
                )
            )

        # Only show non-archived requests by default
        if not include_archived:
            query = query.filter(Request.is_archived == False)

        return query.order_by(desc(Request.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_requests_enhanced(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        status: Optional[RequestStatus] = None,
        search_query: Optional[str] = None,
        include_archived: bool = False,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Request]:
        """Enhanced user requests with status filtering and better search"""
        query = db.query(Request).filter(Request.user_id == user_id)

        # Status filter
        if status:
            query = query.filter(Request.status == status)

        # Search functionality
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Request.request_number.ilike(search_term),
                    Request.unique_code.ilike(search_term),
                    Request.request_title.ilike(search_term),
                    Request.full_name.ilike(search_term),
                    Request.personal_number.ilike(search_term),
                    Request.phone_number.ilike(search_term),
                    Request.building_permit_number.ilike(search_term),
                    Request.building_name.ilike(search_term),
                    Request.civil_defense_file_number.ilike(search_term)
                )
            )

        # Date filters
        if date_from:
            query = query.filter(func.date(Request.created_at) >= date_from)
        if date_to:
            query = query.filter(func.date(Request.created_at) <= date_to)

        # Archive filter
        if not include_archived:
            query = query.filter(Request.is_archived == False)

        return query.order_by(desc(Request.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_requests_count(
        db: Session,
        user_id: int,
        status: Optional[RequestStatus] = None,
        search_query: Optional[str] = None,
        include_archived: bool = False,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> int:
        """Get count of user's requests with filters"""
        query = db.query(Request).filter(Request.user_id == user_id)

        # Status filter
        if status:
            query = query.filter(Request.status == status)

        # Search functionality
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Request.request_number.ilike(search_term),
                    Request.unique_code.ilike(search_term),
                    Request.request_title.ilike(search_term),
                    Request.full_name.ilike(search_term),
                    Request.personal_number.ilike(search_term),
                    Request.phone_number.ilike(search_term),
                    Request.building_permit_number.ilike(search_term),
                    Request.building_name.ilike(search_term),
                    Request.civil_defense_file_number.ilike(search_term)
                )
            )

        # Date filters
        if date_from:
            query = query.filter(func.date(Request.created_at) >= date_from)
        if date_to:
            query = query.filter(func.date(Request.created_at) <= date_to)

        # Archive filter
        if not include_archived:
            query = query.filter(Request.is_archived == False)

        return query.count()

    @staticmethod
    def get_user_request_statistics(db: Session, user_id: int) -> dict:
        """Get request statistics for a specific user"""
        total_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.is_archived == False
        ).count()

        pending_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.PENDING,
            Request.is_archived == False
        ).count()

        in_progress_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.IN_PROGRESS,
            Request.is_archived == False
        ).count()

        completed_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.is_archived == False
        ).count()

        rejected_requests = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.REJECTED,
            Request.is_archived == False
        ).count()

        return {
            "total": total_requests,
            "pending": pending_requests,
            "in_progress": in_progress_requests,
            "completed": completed_requests,
            "rejected": rejected_requests
        }

    @staticmethod
    def delete_request(db: Session, request_id: int) -> bool:
        """Delete a request (hard delete)"""
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            return False

        # Delete associated files first
        files = db.query(File).filter(File.request_id == request_id).all()
        for file in files:
            FileHandler.delete_file(file.file_path)
            db.delete(file)

        # Delete the request
        db.delete(request)
        db.commit()

        return True

    @staticmethod
    def get_all_requests(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        status: Optional[RequestStatus] = None,
        search_query: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Request]:
        """Get all requests with optional status filter and search"""
        query = db.query(Request)

        if status:
            query = query.filter(Request.status == status)

        # Search functionality
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Request.request_number.ilike(search_term),
                    Request.unique_code.ilike(search_term),
                    Request.request_title.ilike(search_term),
                    Request.full_name.ilike(search_term),
                    Request.personal_number.ilike(search_term),
                    Request.phone_number.ilike(search_term),
                    Request.building_permit_number.ilike(search_term)
                )
            )

        # Date filters
        if date_from:
            query = query.filter(func.date(Request.created_at) >= date_from)
        if date_to:
            query = query.filter(func.date(Request.created_at) <= date_to)

        # Only show non-archived requests by default
        query = query.filter(Request.is_archived == False)

        return query.order_by(desc(Request.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_all_requests_count(
        db: Session,
        status: Optional[RequestStatus] = None,
        search_query: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> int:
        """Get count of all requests with optional status filter and search"""
        query = db.query(Request)

        if status:
            query = query.filter(Request.status == status)

        # Search functionality
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Request.request_number.ilike(search_term),
                    Request.unique_code.ilike(search_term),
                    Request.request_title.ilike(search_term),
                    Request.full_name.ilike(search_term),
                    Request.personal_number.ilike(search_term),
                    Request.phone_number.ilike(search_term),
                    Request.building_permit_number.ilike(search_term)
                )
            )

        # Date filters
        if date_from:
            query = query.filter(func.date(Request.created_at) >= date_from)
        if date_to:
            query = query.filter(func.date(Request.created_at) <= date_to)

        # Only show non-archived requests by default
        query = query.filter(Request.is_archived == False)

        return query.count()
    

    
    @staticmethod
    def update_request(
        db: Session,
        request_id: int,
        request_name: Optional[str] = None,
        request_title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[RequestStatus] = None
    ) -> Optional[Request]:
        """Update request information"""
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            return None
        
        if request_name is not None:
            request.request_name = request_name
        
        if request_title is not None:
            request.request_title = request_title
        
        if description is not None:
            request.description = description
        
        if status is not None:
            request.status = status
        
        db.commit()
        db.refresh(request)
        
        return request

    @staticmethod
    def update_civil_defense_request(
        db: Session,
        request_id: int,
        # Civil Defense fields
        full_name: Optional[str] = None,
        personal_number: Optional[str] = None,
        phone_number: Optional[str] = None,
        building_name: Optional[str] = None,
        road_name: Optional[str] = None,
        building_number: Optional[str] = None,
        civil_defense_file_number: Optional[str] = None,
        building_permit_number: Optional[str] = None,
        # Service sections
        licenses_section: Optional[bool] = None,
        fire_equipment_section: Optional[bool] = None,
        commercial_records_section: Optional[bool] = None,
        engineering_offices_section: Optional[bool] = None,
        hazardous_materials_section: Optional[bool] = None,
        # Legacy fields
        request_name: Optional[str] = None,
        request_title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[RequestStatus] = None
    ) -> Optional[Request]:
        """Update request with civil defense form data"""
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            return None

        # Update Civil Defense fields
        if full_name is not None:
            request.full_name = full_name
        if personal_number is not None:
            request.personal_number = personal_number
        if phone_number is not None:
            request.phone_number = phone_number
        if building_name is not None:
            request.building_name = building_name
        if road_name is not None:
            request.road_name = road_name
        if building_number is not None:
            request.building_number = building_number
        if civil_defense_file_number is not None:
            request.civil_defense_file_number = civil_defense_file_number
        if building_permit_number is not None:
            request.building_permit_number = building_permit_number

        # Update service sections
        if licenses_section is not None:
            request.licenses_section = licenses_section
        if fire_equipment_section is not None:
            request.fire_equipment_section = fire_equipment_section
        if commercial_records_section is not None:
            request.commercial_records_section = commercial_records_section
        if engineering_offices_section is not None:
            request.engineering_offices_section = engineering_offices_section
        if hazardous_materials_section is not None:
            request.hazardous_materials_section = hazardous_materials_section

        # Update legacy fields
        if request_name is not None:
            request.request_name = request_name
        if request_title is not None:
            request.request_title = request_title
        if description is not None:
            request.description = description
        if status is not None:
            request.status = status

        db.commit()
        db.refresh(request)

        return request

    @staticmethod
    async def add_files_to_request(
        db: Session,
        request_id: int,
        files: List[UploadFile],
        category: str = "general"
    ) -> Dict[str, Any]:
        """Add files to a request with enhanced validation and error handling"""
        # Check if request exists
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        # Filter out empty files
        valid_files = [f for f in files if f.filename and f.filename.strip()]
        if not valid_files:
            return {
                "saved_files": [],
                "warnings": ["No valid files provided"],
                "errors": []
            }

        # Validate all files before processing
        validation_result = await FileHandler.validate_multiple_files(valid_files)

        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {'; '.join(validation_result['errors'])}"
            )

        saved_files = []
        warnings = validation_result.get("warnings", [])
        errors = []
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                with RequestService._file_upload_lock:
                    RequestService._logger.info(f"Starting file upload for request {request_id}, category '{category}', {len(valid_files)} files")

                    # Get request number for filename generation
                    request_number = request.request_number if request else None
                    RequestService._logger.info(f"Using request number for filename: '{request_number}'")

                    for index, file in enumerate(valid_files):
                        try:
                            RequestService._logger.info(f"Processing file {index + 1}/{len(valid_files)}: '{file.filename}' for category '{category}', request '{request_number}'")

                            # Generate unique filename with category and request - Production Ready
                            field_id = f"{index + 1}"  # Just the number, category and request are already in the filename

                            # Validate filename generation inputs
                            if not file.filename or not file.filename.strip():
                                raise ValueError(f"Invalid filename for file {index + 1}")

                            if not category or not category.strip():
                                raise ValueError(f"Invalid category for file {index + 1}")

                            stored_filename = File.generate_unique_filename(file.filename, category, field_id, request_number)
                            RequestService._logger.info(f"Generated filename: '{file.filename}' -> '{stored_filename}'")

                            # Save file to disk with enhanced validation
                            file_info = await FileHandler.save_file(file, request_id, stored_filename)
                            RequestService._logger.info(f"File saved successfully: '{stored_filename}' ({file_info['file_size']} bytes)")

                            # Add any warnings from file save
                            if file_info.get("warnings"):
                                warnings.extend([f"File '{file.filename}': {w}" for w in file_info["warnings"]])

                            # Create file record in database
                            RequestService._logger.info(f"Creating file record: size={file_info['file_size']} bytes, filename={file_info['stored_filename']}")
                            db_file = File(
                                original_filename=file_info["original_filename"],
                                stored_filename=file_info["stored_filename"],
                                file_path=file_info["file_path"],
                                file_size=file_info["file_size"],
                                file_type=file_info["file_type"],
                                mime_type=file_info["mime_type"],
                                file_category=category,
                                request_id=request_id
                            )

                            db.add(db_file)
                            saved_files.append(db_file)
                            RequestService._logger.info(f"File record added to database: id={db_file.id}, size={db_file.file_size} bytes")

                        except Exception as file_error:
                            errors.append(f"Failed to save '{file.filename}': {str(file_error)}")
                            # Continue with other files instead of failing completely

                    if saved_files:  # Only commit if we have successfully saved files
                        db.commit()

                    break  # Success, exit retry loop

            except (IntegrityError, OperationalError) as e:
                db.rollback()
                retry_count += 1
                error_msg = f"Database error (attempt {retry_count}): {str(e)}"
                errors.append(error_msg)

                # Clean up any saved files on database error
                for file in saved_files:
                    if hasattr(file, 'file_path'):
                        FileHandler.delete_file(file.file_path)
                saved_files = []  # Reset for retry

                if retry_count >= max_retries:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Database error after {max_retries} attempts: {'; '.join(errors)}"
                    )

                # Wait before retry
                time.sleep(0.1 * (2 ** retry_count))

            except Exception as e:
                db.rollback()
                error_msg = f"Unexpected error: {str(e)}"
                errors.append(error_msg)

                # Clean up any saved files
                for file in saved_files:
                    if hasattr(file, 'file_path'):
                        FileHandler.delete_file(file.file_path)

                # If we have partial success, return what we can
                if saved_files and len(errors) < len(valid_files):
                    warnings.append(f"Some files failed: {error_msg}")
                    return {
                        "saved_files": saved_files,
                        "warnings": warnings,
                        "errors": errors,
                        "partial_success": True
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"File upload failed: {error_msg}"
                    )

        # Refresh all files
        for file in saved_files:
            db.refresh(file)

        return {
            "saved_files": saved_files,
            "warnings": warnings,
            "errors": errors,
            "total_files_processed": len(valid_files),
            "successful_uploads": len(saved_files)
        }

    @staticmethod
    async def add_categorized_files_to_request(
        db: Session,
        request_id: int,
        file_categories: Dict[str, List[UploadFile]]
    ) -> Dict[str, List[File]]:
        """Add multiple file categories to a request"""
        # Check if request exists
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        all_saved_files = {}

        try:
            for category, files in file_categories.items():
                if files:  # Only process if files exist for this category
                    upload_result = await RequestService.add_files_to_request(
                        db, request_id, files, category
                    )
                    # Extract the saved files from the result dictionary
                    if isinstance(upload_result, dict):
                        all_saved_files[category] = upload_result.get("saved_files", [])
                    else:
                        # Backward compatibility if it returns a list directly
                        all_saved_files[category] = upload_result

            return all_saved_files

        except Exception as e:
            # If any category fails, rollback everything
            db.rollback()
            raise e
    
    @staticmethod
    def delete_file_from_request(db: Session, file_id: int) -> bool:
        """Delete a file from a request"""
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            return False
        
        # Delete file from disk
        FileHandler.delete_file(file.file_path)
        
        # Delete file record from database
        db.delete(file)
        db.commit()
        
        return True

    @staticmethod
    def archive_request(db: Session, request_id: int) -> bool:
        """Archive request (soft delete)"""
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            return False

        request.is_archived = True
        db.commit()

        return True

    @staticmethod
    def restore_request(db: Session, request_id: int) -> bool:
        """Restore archived request"""
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            return False

        request.is_archived = False
        db.commit()

        return True

    @staticmethod
    def get_archived_requests(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        user_id: Optional[int] = None,
        search_query: Optional[str] = None
    ) -> List[Request]:
        """Get archived requests with optional search"""
        query = db.query(Request).filter(Request.is_archived == True)

        if user_id:
            query = query.filter(Request.user_id == user_id)

        # Search functionality
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Request.request_number.ilike(search_term),
                    Request.unique_code.ilike(search_term),
                    Request.request_title.ilike(search_term),
                    Request.full_name.ilike(search_term),
                    Request.personal_number.ilike(search_term),
                    Request.phone_number.ilike(search_term),
                    Request.building_permit_number.ilike(search_term)
                )
            )

        return query.order_by(desc(Request.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_request_statistics(db: Session) -> dict:
        """Get request statistics"""
        total_requests = db.query(Request).count()
        pending_requests = db.query(Request).filter(Request.status == RequestStatus.PENDING).count()
        in_progress_requests = db.query(Request).filter(Request.status == RequestStatus.IN_PROGRESS).count()
        completed_requests = db.query(Request).filter(Request.status == RequestStatus.COMPLETED).count()
        rejected_requests = db.query(Request).filter(Request.status == RequestStatus.REJECTED).count()

        return {
            "total": total_requests,
            "pending": pending_requests,
            "in_progress": in_progress_requests,
            "completed": completed_requests,
            "rejected": rejected_requests
        }

    @staticmethod
    def get_user_monthly_chart_data(db: Session, months_back: int = 12) -> Dict[str, Any]:
        """Get monthly completed requests data for users with 'user' role for chart display"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)

        # Get users with 'user' role only - limit to prevent connection exhaustion
        users_with_user_role = db.query(User).filter(
            User.role == UserRole.USER,
            User.is_active == True
        ).limit(10).all()  # Limit to 10 users for chart display

        # Arabic month names
        arabic_months = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]

        # Generate month labels for the last 12 months
        month_labels = []
        current_date = end_date.replace(day=1)  # Start from first day of month to avoid day overflow
        for i in range(months_back):
            month_labels.insert(0, arabic_months[current_date.month - 1])
            # Move to previous month safely
            if current_date.month == 1:
                current_date = current_date.replace(year=current_date.year - 1, month=12, day=1)
            else:
                current_date = current_date.replace(month=current_date.month - 1, day=1)

        # Prepare datasets for each user
        datasets = []
        colors = [
            '#5e72e4', '#11cdef', '#2dce89', '#fb6340', '#f5365c',
            '#ffd600', '#36b9cc', '#6f42c1', '#e83e8c', '#fd7e14'
        ]

        for idx, user in enumerate(users_with_user_role):
            # Get completed requests for this user grouped by month
            monthly_data = []
            current_date = end_date.replace(day=1)  # Start from first day of month

            for month_idx in range(months_back):
                # Calculate start and end of the month safely
                month_start = current_date.replace(day=1)

                # Calculate next month's first day, then subtract 1 day to get end of current month
                if current_date.month == 12:
                    next_month_start = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    next_month_start = current_date.replace(month=current_date.month + 1, day=1)
                month_end = next_month_start - timedelta(days=1)

                # Count completed requests for this user in this month
                completed_count = db.query(Request).filter(
                    Request.user_id == user.id,
                    Request.status == RequestStatus.COMPLETED,
                    Request.created_at >= month_start,
                    Request.created_at <= month_end
                ).count()

                monthly_data.insert(0, completed_count)

                # Move to previous month safely
                if current_date.month == 1:
                    current_date = current_date.replace(year=current_date.year - 1, month=12, day=1)
                else:
                    current_date = current_date.replace(month=current_date.month - 1, day=1)

            # Only include users who have at least one completed request
            if sum(monthly_data) > 0:
                color = colors[idx % len(colors)]
                datasets.append({
                    'label': user.full_name,
                    'data': monthly_data,
                    'borderColor': color,
                    'backgroundColor': color + '20',  # Add transparency
                    'pointBackgroundColor': color,
                    'pointBorderColor': '#ffffff',
                    'pointBorderWidth': 2,
                    'pointRadius': 6,
                    'pointHoverRadius': 8,
                    'borderWidth': 3,
                    'fill': False,
                    'tension': 0.4,
                    'user_id': user.id,
                    'username': user.username
                })

        return {
            'labels': month_labels,
            'datasets': datasets
        }



    @staticmethod
    def get_user_achievements_data(db: Session, page: int = 1, filter_type: str = "all", per_page: int = 12) -> Dict[str, Any]:
        """Get user achievements data for the achievements page"""
        # Base query for users with 'user' role only
        query = db.query(User).filter(
            User.role == UserRole.USER,
            User.is_active == True
        )

        # For high-achievers filter, we need to get all users first then filter
        if filter_type == "high-achievers":
            # Get all users, then filter by completion rate
            all_users = query.all()
            high_achiever_users = []

            for user in all_users:
                total_requests = db.query(Request).filter(Request.user_id == user.id).count()
                if total_requests > 0:
                    completed_requests = db.query(Request).filter(
                        Request.user_id == user.id,
                        Request.status == RequestStatus.COMPLETED
                    ).count()
                    completion_rate = (completed_requests / total_requests * 100)
                    if completion_rate >= 80:
                        high_achiever_users.append(user)

            # Apply pagination to filtered users
            total_users = len(high_achiever_users)
            total_pages = (total_users + per_page - 1) // per_page
            offset = (page - 1) * per_page
            users = high_achiever_users[offset:offset + per_page]

        elif filter_type == "active":
            # Users active in the last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.filter(User.updated_at >= week_ago)
            total_users = query.count()
            total_pages = (total_users + per_page - 1) // per_page
            offset = (page - 1) * per_page
            users = query.offset(offset).limit(per_page).all()

        elif filter_type == "new":
            # Users created in the last 30 days
            month_ago = datetime.utcnow() - timedelta(days=30)
            query = query.filter(User.created_at >= month_ago)
            total_users = query.count()
            total_pages = (total_users + per_page - 1) // per_page
            offset = (page - 1) * per_page
            users = query.offset(offset).limit(per_page).all()

        else:
            # All users
            total_users = query.count()
            total_pages = (total_users + per_page - 1) // per_page
            offset = (page - 1) * per_page
            users = query.offset(offset).limit(per_page).all()

        user_achievements = []

        for user in users:
            # Get user's request statistics
            total_requests = db.query(Request).filter(Request.user_id == user.id).count()
            completed_requests = db.query(Request).filter(
                Request.user_id == user.id,
                Request.status == RequestStatus.COMPLETED
            ).count()

            # Calculate completion rate
            completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0



            # Determine user category and status
            category = "regular"
            status_text = "عادي"

            if completion_rate >= 90:
                category = "high-achievers"
                status_text = "متفوق"
            elif completion_rate >= 70:
                category = "active"
                status_text = "نشط"
            elif (datetime.utcnow() - (user.created_at.replace(tzinfo=None) if user.created_at.tzinfo else user.created_at)).days <= 30:
                category = "new"
                status_text = "جديد"

            # Generate user initials
            name_parts = user.full_name.split()
            initials = name_parts[0][0] + (name_parts[1][0] if len(name_parts) > 1 else "")

            # Generate achievement badges
            badges = []
            if completion_rate >= 90:
                badges.append({
                    "name": "متفوق",
                    "type": "gold",
                    "description": "معدل إنجاز أكثر من 90%"
                })
            if completion_rate >= 70:
                badges.append({
                    "name": "نشط",
                    "type": "silver",
                    "description": "معدل إنجاز أكثر من 70%"
                })
            if total_requests >= 10:
                badges.append({
                    "name": "منتج",
                    "type": "bronze",
                    "description": "أكثر من 10 طلبات"
                })

            # Calculate last activity
            last_request = db.query(Request).filter(Request.user_id == user.id).order_by(Request.created_at.desc()).first()
            if last_request:
                # Handle timezone-aware datetime
                if last_request.created_at.tzinfo is not None:
                    # Convert to naive datetime for comparison
                    last_request_time = last_request.created_at.replace(tzinfo=None)
                else:
                    last_request_time = last_request.created_at

                days_ago = (datetime.utcnow() - last_request_time).days
                if days_ago == 0:
                    last_activity = "اليوم"
                elif days_ago == 1:
                    last_activity = "أمس"
                else:
                    last_activity = f"منذ {days_ago} أيام"
            else:
                last_activity = "لا يوجد نشاط"

            user_achievement = {
                'user_id': user.id,
                'full_name': user.full_name,
                'username': user.username,
                'category': category,

                'status_text': status_text,

                'initials': initials,
                'total_requests': total_requests,
                'completed_requests': completed_requests,
                'achievement_score': round(completion_rate, 1),
                'badges': badges,
                'last_activity': last_activity
            }

            user_achievements.append(user_achievement)

        return {
            'users': user_achievements,
            'total_pages': total_pages,
            'current_page': page,
            'total_users': len(user_achievements)
        }



    @staticmethod
    def get_achievements_statistics(db: Session) -> Dict[str, int]:
        """Get statistics for the achievements page"""
        from datetime import datetime, timedelta

        # Total users with 'user' role
        total_users = db.query(User).filter(
            User.role == UserRole.USER,
            User.is_active == True
        ).count()

        # High achievers (users with >80% completion rate)
        high_achievers_count = 0
        users = db.query(User).filter(User.role == UserRole.USER, User.is_active == True).all()

        for user in users:
            total_requests = db.query(Request).filter(Request.user_id == user.id).count()
            if total_requests > 0:
                completed_requests = db.query(Request).filter(
                    Request.user_id == user.id,
                    Request.status == RequestStatus.COMPLETED
                ).count()
                completion_rate = (completed_requests / total_requests * 100)
                if completion_rate >= 80:
                    high_achievers_count += 1

        # Active users (active in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users_count = db.query(User).filter(
            User.role == UserRole.USER,
            User.is_active == True,
            User.updated_at >= week_ago
        ).count()

        # New users (created in last 30 days)
        month_ago = datetime.utcnow() - timedelta(days=30)
        new_users_count = db.query(User).filter(
            User.role == UserRole.USER,
            User.is_active == True,
            User.created_at >= month_ago
        ).count()

        # Total achievements (sum of all badges earned)
        total_achievements = high_achievers_count * 2 + active_users_count  # Simplified calculation

        return {
            'total_users': total_users,
            'high_achievers_count': high_achievers_count,
            'active_users_count': active_users_count,
            'new_users_count': new_users_count,
            'total_achievements': total_achievements
        }

    @staticmethod
    def get_user_progress_tracking(db: Session) -> List[Dict[str, Any]]:
        """
        Get comprehensive user progress tracking data for admin dashboard
        Modern implementation with realistic goals and enhanced user experience
        """
        from sqlalchemy import func
        from datetime import datetime, timedelta

        # Get active users with 'user' role (limit for performance)
        users = db.query(User).filter(
            User.role == UserRole.USER,
            User.is_active == True
        ).limit(25).all()  # Reasonable limit for admin dashboard

        if not users:
            return []

        # Time period calculations
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Business week calculations (last 5 business days)
        business_week_start = RequestService._get_business_days_start(now, 5)
        week_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Month calculations
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
        else:
            month_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)

        # Realistic goals configuration
        GOALS = {
            'daily': 3,    # 3 requests per day (achievable)
            'weekly': 12,  # 12 requests per 5 business days (realistic - ~2.4 per day)
            'monthly': 50  # 50 requests per month (challenging but fair)
        }

        # Get all user IDs for optimized queries
        user_ids = [user.id for user in users]

        # Optimized bulk queries for all time periods
        daily_counts = dict(db.query(
            Request.user_id,
            func.count(Request.id).label('count')
        ).filter(
            Request.user_id.in_(user_ids),
            Request.status == RequestStatus.COMPLETED,
            Request.created_at >= today_start,
            Request.created_at <= today_end
        ).group_by(Request.user_id).all())

        weekly_counts = dict(db.query(
            Request.user_id,
            func.count(Request.id).label('count')
        ).filter(
            Request.user_id.in_(user_ids),
            Request.status == RequestStatus.COMPLETED,
            Request.created_at >= business_week_start,
            Request.created_at <= week_end
        ).group_by(Request.user_id).all())

        monthly_counts = dict(db.query(
            Request.user_id,
            func.count(Request.id).label('count')
        ).filter(
            Request.user_id.in_(user_ids),
            Request.status == RequestStatus.COMPLETED,
            Request.created_at >= month_start,
            Request.created_at <= month_end
        ).group_by(Request.user_id).all())

        # Build progress data for each user
        progress_data = []

        for user in users:
            user_id = user.id

            # Get completion counts
            daily_completed = daily_counts.get(user_id, 0)
            weekly_completed = weekly_counts.get(user_id, 0)
            monthly_completed = monthly_counts.get(user_id, 0)

            # Calculate progress metrics
            daily_progress = RequestService._calculate_period_progress(
                daily_completed, GOALS['daily'], "اليومي", "bi-sun"
            )
            weekly_progress = RequestService._calculate_period_progress(
                weekly_completed, GOALS['weekly'], "الأسبوعي", "bi-calendar-week"
            )
            monthly_progress = RequestService._calculate_period_progress(
                monthly_completed, GOALS['monthly'], "الشهري", "bi-calendar-month"
            )

            # Calculate user achievements
            total_requests = db.query(Request).filter(Request.user_id == user_id).count()
            total_completed = db.query(Request).filter(
                Request.user_id == user_id,
                Request.status == RequestStatus.COMPLETED
            ).count()

            completion_rate = (total_completed / total_requests * 100) if total_requests > 0 else 0



            # Determine overall status
            avg_percentage = (daily_progress['percentage'] + weekly_progress['percentage'] + monthly_progress['percentage']) / 3
            if avg_percentage >= 80:
                status_text = "ممتاز"
            elif avg_percentage >= 60:
                status_text = "جيد"
            else:
                status_text = "يحتاج تحسين"

            # Build user progress object
            user_progress = {
                'user_id': user_id,
                'user_info': {
                    'full_name': user.full_name,
                    'username': user.username,


                    'status_text': status_text
                },
                'time_periods': {
                    'daily': daily_progress,
                    'weekly': weekly_progress,
                    'monthly': monthly_progress
                },
                'achievements': {
                    'total_completed': total_completed,
                    'completion_rate': round(completion_rate, 1),
                    'total_requests': total_requests
                },
                'overall_percentage': round(avg_percentage, 1)
            }

            progress_data.append(user_progress)

        # Sort by overall performance (best performers first)
        progress_data.sort(key=lambda x: x['overall_percentage'], reverse=True)

        return progress_data

    @staticmethod
    def _calculate_period_progress(completed: int, goal: int, period_name: str, icon: str) -> Dict[str, Any]:
        """
        Calculate progress metrics for a specific time period
        """
        # Calculate percentage (capped at 100%)
        percentage = min(100.0, (completed / goal) * 100) if goal > 0 else 0.0

        # Calculate remaining
        remaining = max(0, goal - completed)

        # Determine status and color scheme
        if percentage >= 100:
            status = "excellent"
            color_scheme = "success"
        elif percentage >= 70:
            status = "good"
            color_scheme = "warning"
        else:
            status = "needs_improvement"
            color_scheme = "danger"

        # Generate Arabic remaining text
        remaining_text = RequestService._format_arabic_remaining_text(remaining, period_name)

        return {
            'period_name': period_name,
            'icon': icon,
            'goal': goal,
            'completed': completed,
            'percentage': round(percentage, 1),
            'status': status,
            'remaining': remaining,
            'remaining_text': remaining_text,
            'color_scheme': color_scheme
        }

    @staticmethod
    def _format_arabic_remaining_text(remaining: int, period_type: str) -> str:
        """
        Format remaining requests text in proper Arabic grammar
        """
        if remaining == 0:
            return "🎉 تم تحقيق الهدف!"
        elif remaining == 1:
            return f"طلب واحد متبقي لتحقيق الهدف {period_type}"
        elif remaining == 2:
            return f"طلبان متبقيان لتحقيق الهدف {period_type}"
        elif 3 <= remaining <= 10:
            return f"{remaining} طلبات متبقية لتحقيق الهدف {period_type}"
        else:
            return f"{remaining} طلباً متبقياً لتحقيق الهدف {period_type}"

    @staticmethod
    def get_user_personal_progress(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Get personal progress tracking data for individual user dashboard
        Enhanced with motivational elements and achievements
        """
        from datetime import datetime, timedelta

        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Time period calculations (same as admin version)
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Week calculations (Monday to Sunday)
        days_since_monday = now.weekday()
        week_start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = (week_start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)

        # Month calculations
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
        else:
            month_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)

        # Realistic goals configuration
        GOALS = {
            'daily': 3,    # 3 requests per day
            'weekly': 15,  # 15 requests per week
            'monthly': 50  # 50 requests per month
        }

        # Count completed requests for each period
        daily_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.created_at >= today_start,
            Request.created_at <= today_end
        ).count()

        weekly_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.created_at >= week_start,
            Request.created_at <= week_end
        ).count()

        monthly_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED,
            Request.created_at >= month_start,
            Request.created_at <= month_end
        ).count()

        # Calculate progress for each period
        daily_progress = RequestService._calculate_period_progress(
            daily_completed, GOALS['daily'], "اليومي", "bi-sun"
        )
        weekly_progress = RequestService._calculate_period_progress(
            weekly_completed, GOALS['weekly'], "الأسبوعي", "bi-calendar-week"
        )
        monthly_progress = RequestService._calculate_period_progress(
            monthly_completed, GOALS['monthly'], "الشهري", "bi-calendar-month"
        )

        # Calculate overall achievements
        total_requests = db.query(Request).filter(Request.user_id == user_id).count()
        total_completed = db.query(Request).filter(
            Request.user_id == user_id,
            Request.status == RequestStatus.COMPLETED
        ).count()

        completion_rate = (total_completed / total_requests * 100) if total_requests > 0 else 0

        # Calculate streak (consecutive days with activity)
        streak_days = RequestService._calculate_activity_streak(db, user_id)

        # Generate motivational content
        motivation = RequestService._generate_motivation_content(
            daily_progress, weekly_progress, monthly_progress, completion_rate, streak_days
        )

        # Generate achievement badges
        badges = RequestService._generate_achievement_badges(
            total_completed, completion_rate, streak_days
        )

        # Calculate overall performance
        avg_percentage = (daily_progress['percentage'] + weekly_progress['percentage'] + monthly_progress['percentage']) / 3

        return {
            'user_id': user_id,
            'user_info': {
                'full_name': user.full_name,
                'username': user.username
            },
            'time_periods': {
                'daily': daily_progress,
                'weekly': weekly_progress,
                'monthly': monthly_progress
            },
            'achievements': {
                'total_completed': total_completed,
                'completion_rate': round(completion_rate, 1),
                'total_requests': total_requests,
                'streak_days': streak_days,
                'badges': badges
            },
            'motivation': motivation,
            'overall_percentage': round(avg_percentage, 1)
        }

    @staticmethod
    def _calculate_activity_streak(db: Session, user_id: int) -> int:
        """
        Calculate consecutive days with completed requests (activity streak)
        """
        from datetime import datetime, timedelta

        now = datetime.now()
        streak_days = 0
        current_date = now.date()

        # Check last 30 days for streak calculation
        for i in range(30):
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            # Check if user had any completed requests on this day
            daily_count = db.query(Request).filter(
                Request.user_id == user_id,
                Request.status == RequestStatus.COMPLETED,
                Request.created_at >= day_start,
                Request.created_at <= day_end
            ).count()

            if daily_count > 0:
                streak_days += 1
                current_date -= timedelta(days=1)
            else:
                break  # Streak broken

        return streak_days

    @staticmethod
    def _generate_motivation_content(daily_progress: Dict, weekly_progress: Dict,
                                   monthly_progress: Dict, completion_rate: float,
                                   streak_days: int) -> Dict[str, Any]:
        """
        Generate motivational messages and next milestones based on user progress
        """
        avg_percentage = (daily_progress['percentage'] + weekly_progress['percentage'] + monthly_progress['percentage']) / 3

        # Determine encouragement level
        if avg_percentage >= 80:
            encouragement_level = "high"
            if streak_days >= 7:
                message = "🔥 أداء رائع! أنت في المقدمة ولديك سلسلة إنجازات ممتازة!"
            elif completion_rate >= 90:
                message = "⭐ إنجاز متميز! معدل إكمالك ممتاز، استمر على هذا المستوى!"
            else:
                message = "👏 عمل ممتاز! أنت تحقق أهدافك بنجاح، استمر في التقدم!"
        elif avg_percentage >= 50:
            encouragement_level = "medium"
            if daily_progress['remaining'] <= 1:
                message = "💪 أنت قريب من تحقيق هدفك اليومي! طلب واحد فقط وستصل!"
            elif weekly_progress['percentage'] > daily_progress['percentage']:
                message = "📈 تقدم جيد هذا الأسبوع! ركز على الأهداف اليومية لتحسين الأداء."
            else:
                message = "🎯 أداء جيد! يمكنك تحسين النتائج بقليل من الجهد الإضافي."
        else:
            encouragement_level = "low"
            if streak_days == 0:
                message = "🚀 ابدأ رحلتك اليوم! كل إنجاز كبير يبدأ بخطوة صغيرة."
            elif daily_progress['completed'] == 0:
                message = "⏰ لم تبدأ بعد اليوم؟ لا تقلق، لا يزال هناك وقت لتحقيق هدفك!"
            else:
                message = "💡 بداية جيدة! استمر في العمل وستحقق أهدافك قريباً."

        # Determine next milestone
        if daily_progress['remaining'] > 0:
            next_milestone = f"إكمال {daily_progress['remaining']} طلب لتحقيق الهدف اليومي"
        elif weekly_progress['remaining'] > 0:
            next_milestone = f"إكمال {weekly_progress['remaining']} طلب لتحقيق الهدف الأسبوعي"
        elif monthly_progress['remaining'] > 0:
            next_milestone = f"إكمال {monthly_progress['remaining']} طلب لتحقيق الهدف الشهري"
        else:
            next_milestone = "🏆 تم تحقيق جميع الأهداف! أنت بطل!"

        return {
            'message': message,
            'next_milestone': next_milestone,
            'encouragement_level': encouragement_level
        }

    @staticmethod
    def _generate_achievement_badges(total_completed: int, completion_rate: float,
                                   streak_days: int) -> List[Dict[str, Any]]:
        """
        Generate achievement badges based on user performance
        """
        badges = []

        # Completion rate badges
        if completion_rate >= 95:
            badges.append({
                'name': 'الكمال',
                'icon': 'bi-gem',
                'type': 'diamond',
                'description': 'معدل إكمال أكثر من 95%'
            })
        elif completion_rate >= 90:
            badges.append({
                'name': 'متفوق',
                'icon': 'bi-trophy-fill',
                'type': 'gold',
                'description': 'معدل إكمال أكثر من 90%'
            })
        elif completion_rate >= 75:
            badges.append({
                'name': 'نشط',
                'icon': 'bi-star-fill',
                'type': 'silver',
                'description': 'معدل إكمال أكثر من 75%'
            })
        elif completion_rate >= 50:
            badges.append({
                'name': 'منتظم',
                'icon': 'bi-award-fill',
                'type': 'bronze',
                'description': 'معدل إكمال أكثر من 50%'
            })

        # Total completion badges
        if total_completed >= 100:
            badges.append({
                'name': 'المئوية',
                'icon': 'bi-hundred',
                'type': 'gold',
                'description': 'أكمل 100 طلب أو أكثر'
            })
        elif total_completed >= 50:
            badges.append({
                'name': 'الخمسينية',
                'icon': 'bi-50-circle',
                'type': 'silver',
                'description': 'أكمل 50 طلب أو أكثر'
            })
        elif total_completed >= 25:
            badges.append({
                'name': 'الربعية',
                'icon': 'bi-25-circle',
                'type': 'bronze',
                'description': 'أكمل 25 طلب أو أكثر'
            })
        elif total_completed >= 10:
            badges.append({
                'name': 'العشرية',
                'icon': 'bi-10-circle',
                'type': 'bronze',
                'description': 'أكمل 10 طلبات أو أكثر'
            })

        # Streak badges
        if streak_days >= 30:
            badges.append({
                'name': 'الشهري',
                'icon': 'bi-fire',
                'type': 'diamond',
                'description': f'نشاط متواصل لمدة {streak_days} يوم'
            })
        elif streak_days >= 14:
            badges.append({
                'name': 'الأسبوعين',
                'icon': 'bi-lightning-fill',
                'type': 'gold',
                'description': f'نشاط متواصل لمدة {streak_days} يوم'
            })
        elif streak_days >= 7:
            badges.append({
                'name': 'الأسبوعي',
                'icon': 'bi-calendar-check',
                'type': 'silver',
                'description': f'نشاط متواصل لمدة {streak_days} أيام'
            })
        elif streak_days >= 3:
            badges.append({
                'name': 'المتواصل',
                'icon': 'bi-arrow-up-circle',
                'type': 'bronze',
                'description': f'نشاط متواصل لمدة {streak_days} أيام'
            })

        return badges

    @staticmethod
    def update_request_status(db: Session, request_id: int, new_status: RequestStatus, updated_by: int) -> Request:
        """Update request status and trigger achievement updates if completed"""
        request = db.query(Request).filter(Request.id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        old_status = request.status
        request.status = new_status
        request.updated_at = datetime.utcnow()

        # If request is being marked as completed, update achievements
        if new_status == RequestStatus.COMPLETED and old_status != RequestStatus.COMPLETED:
            # Import here to avoid circular imports
            from app.services.achievement_service import AchievementService
            AchievementService.update_user_progress(db, request.user_id, completed_requests=1)

        db.commit()
        db.refresh(request)

        return request

    @staticmethod
    def get_requests_by_user_id(
        db: Session,
        user_id: int,
        status: Optional[RequestStatus] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Request]:
        """Get requests for a specific user with optional filtering"""
        try:
            query = db.query(Request).filter(Request.user_id == user_id)

            # Apply status filter
            if status:
                query = query.filter(Request.status == status)

            # Apply search filter
            if search_query:
                search_term = f"%{search_query}%"
                query = query.filter(
                    or_(
                        Request.request_number.ilike(search_term),
                        Request.full_name.ilike(search_term),
                        Request.personal_number.ilike(search_term),
                        Request.phone_number.ilike(search_term),
                        Request.building_name.ilike(search_term),
                        Request.building_permit_number.ilike(search_term),
                        Request.unique_code.ilike(search_term)
                    )
                )

            # Order by creation date (newest first)
            query = query.order_by(desc(Request.created_at))

            # Apply pagination
            query = query.offset(skip).limit(limit)

            return query.all()

        except Exception as e:
            RequestService._logger.error(f"Error getting requests for user {user_id}: {e}")
            return []

    @staticmethod
    def get_user_request_statistics(db: Session, user_id: int) -> Dict[str, Any]:
        """Get request statistics for a specific user"""
        try:
            # Get total requests count
            total_requests = db.query(Request).filter(Request.user_id == user_id).count()

            # Get status distribution
            status_distribution = {}
            for status in RequestStatus:
                count = db.query(Request).filter(
                    Request.user_id == user_id,
                    Request.status == status
                ).count()
                status_distribution[status.value] = count

            # Get time-based statistics
            now = datetime.now()

            # Daily statistics (last 24 hours)
            one_day_ago = now - timedelta(days=1)
            daily_requests = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= one_day_ago
            ).count()
            daily_completed = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= one_day_ago,
                Request.status == RequestStatus.COMPLETED
            ).count()
            daily_completion_rate = (daily_completed / daily_requests * 100) if daily_requests > 0 else 0

            # Weekly statistics (last 5 business days)
            # Calculate the start of the last 5 business days
            business_days_start = RequestService._get_business_days_start(now, 5)
            weekly_requests = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= business_days_start
            ).count()
            weekly_completed = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= business_days_start,
                Request.status == RequestStatus.COMPLETED
            ).count()
            weekly_completion_rate = (weekly_completed / weekly_requests * 100) if weekly_requests > 0 else 0

            # Monthly statistics (last 30 days)
            one_month_ago = now - timedelta(days=30)
            monthly_requests = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= one_month_ago
            ).count()
            monthly_completed = db.query(Request).filter(
                Request.user_id == user_id,
                Request.created_at >= one_month_ago,
                Request.status == RequestStatus.COMPLETED
            ).count()
            monthly_completion_rate = (monthly_completed / monthly_requests * 100) if monthly_requests > 0 else 0

            # Overall completion rate
            completed_requests = status_distribution.get('completed', 0)
            overall_completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0

            return {
                'total_requests': total_requests,
                'status_distribution': status_distribution,
                'overall_completion_rate': round(overall_completion_rate, 1),
                'daily_stats': {
                    'requests': daily_requests,
                    'completed': daily_completed,
                    'completion_rate': round(daily_completion_rate, 1)
                },
                'weekly_stats': {
                    'requests': weekly_requests,
                    'completed': weekly_completed,
                    'completion_rate': round(weekly_completion_rate, 1)
                },
                'monthly_stats': {
                    'requests': monthly_requests,
                    'completed': monthly_completed,
                    'completion_rate': round(monthly_completion_rate, 1)
                }
            }

        except Exception as e:
            RequestService._logger.error(f"Error getting user request statistics for user {user_id}: {e}")
            return {
                'total_requests': 0,
                'status_distribution': {},
                'overall_completion_rate': 0,
                'daily_stats': {'requests': 0, 'completed': 0, 'completion_rate': 0},
                'weekly_stats': {'requests': 0, 'completed': 0, 'completion_rate': 0},
                'monthly_stats': {'requests': 0, 'completed': 0, 'completion_rate': 0}
            }

    @staticmethod
    def _get_business_days_start(current_date: datetime, business_days: int) -> datetime:
        """Calculate the start date for the last N business days (excluding weekends)"""
        days_counted = 0
        check_date = current_date

        while days_counted < business_days:
            check_date = check_date - timedelta(days=1)
            # Monday = 0, Sunday = 6
            # Skip weekends (Saturday = 5, Sunday = 6)
            if check_date.weekday() < 5:  # Monday to Friday
                days_counted += 1

        # Return the start of that business day
        return check_date.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def get_users_competition_data(db: Session) -> List[Dict[str, Any]]:
        """Get users competition data for bubble chart visualization"""
        try:
            from app.services.avatar_service import AvatarService

            # Get all active users (excluding admins for fair competition)
            users = db.query(User).filter(
                User.is_active == True,
                User.role == UserRole.USER  # Only regular users in competition
            ).all()

            if not users:
                return []

            competition_data = []
            now = datetime.now()

            # Calculate time periods
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            business_week_start = RequestService._get_business_days_start(now, 5)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            for user in users:
                # Get user's avatar URL
                avatar_url = AvatarService.get_avatar_url(user.id, user.full_name, db)

                # Daily completed requests
                daily_completed = db.query(Request).filter(
                    Request.user_id == user.id,
                    Request.status == RequestStatus.COMPLETED,
                    Request.created_at >= today_start
                ).count()

                # Weekly completed requests (5 business days)
                weekly_completed = db.query(Request).filter(
                    Request.user_id == user.id,
                    Request.status == RequestStatus.COMPLETED,
                    Request.created_at >= business_week_start
                ).count()

                # Monthly completed requests
                monthly_completed = db.query(Request).filter(
                    Request.user_id == user.id,
                    Request.status == RequestStatus.COMPLETED,
                    Request.created_at >= month_start
                ).count()

                # Total completed requests (all time)
                total_completed = db.query(Request).filter(
                    Request.user_id == user.id,
                    Request.status == RequestStatus.COMPLETED
                ).count()

                # Calculate performance score (weighted average)
                # Daily: 40%, Weekly: 35%, Monthly: 25%
                daily_score = min(100, (daily_completed / 3) * 100)  # Max 3 per day
                weekly_score = min(100, (weekly_completed / 12) * 100)  # Max 12 per week
                monthly_score = min(100, (monthly_completed / 50) * 100)  # Max 50 per month

                performance_score = (daily_score * 0.4) + (weekly_score * 0.35) + (monthly_score * 0.25)

                # Determine bubble size based on total completed requests
                # Size range: 30-100 pixels
                min_size = 30
                max_size = 100
                max_requests = 200  # Assume max 200 requests for scaling
                bubble_size = min_size + ((total_completed / max_requests) * (max_size - min_size))
                bubble_size = min(max_size, max(min_size, bubble_size))

                # Determine performance level and color
                if performance_score >= 80:
                    level = "ممتاز"
                    color = "#10B981"  # Green
                elif performance_score >= 60:
                    level = "جيد جداً"
                    color = "#3B82F6"  # Blue
                elif performance_score >= 40:
                    level = "جيد"
                    color = "#F59E0B"  # Yellow
                elif performance_score >= 20:
                    level = "مقبول"
                    color = "#EF4444"  # Red
                else:
                    level = "ضعيف"
                    color = "#6B7280"  # Gray

                competition_data.append({
                    'user_id': user.id,
                    'name': user.full_name or user.username,
                    'email': user.email,
                    'avatar_url': avatar_url,
                    'daily_completed': daily_completed,
                    'weekly_completed': weekly_completed,
                    'monthly_completed': monthly_completed,
                    'total_completed': total_completed,
                    'performance_score': round(performance_score, 1),
                    'bubble_size': round(bubble_size),
                    'level': level,
                    'color': color,
                    'position_x': 0,  # Will be calculated in frontend
                    'position_y': 0   # Will be calculated in frontend
                })

            # Sort by performance score (highest first)
            competition_data.sort(key=lambda x: x['performance_score'], reverse=True)

            return competition_data

        except Exception as e:
            RequestService._logger.error(f"Error getting users competition data: {e}")
            return []


