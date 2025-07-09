from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


class RequestStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String(50), unique=True, index=True, nullable=False)
    unique_code = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Legacy fields for backward compatibility (nullable for civil defense forms)
    request_name = Column(String(200), nullable=True)
    request_title = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)

    # Personal Information
    full_name = Column(String(200), nullable=True)  # الإسم الثلاثي
    personal_number = Column(String(9), nullable=True)  # الرقم الشخصي (9 digits exactly)
    phone_number = Column(String(15), nullable=True)  # رقم الهاتف

    # Building Information
    building_name = Column(String(200), nullable=True)  # المبنى
    road_name = Column(String(200), nullable=True)  # الطريق
    building_number = Column(String(100), nullable=True)  # المجمع
    civil_defense_file_number = Column(String(100), nullable=True)  # رقم ملف الدفاع المدني
    building_permit_number = Column(String(100), nullable=True)  # رقم إجازة البناء

    # License Sections (Checkboxes)
    licenses_section = Column(Boolean, default=False, nullable=False)  # قسم التراخيص
    fire_equipment_section = Column(Boolean, default=False, nullable=False)  # قسم معدات مقاومة الحريق
    commercial_records_section = Column(Boolean, default=False, nullable=False)  # قسم تراخيص السجلات التجارية
    engineering_offices_section = Column(Boolean, default=False, nullable=False)  # قسم تراخيص وتجديد المكاتب الهندسية
    hazardous_materials_section = Column(Boolean, default=False, nullable=False)  # قسم المواد الخطرة

    # Relationships
    user = relationship("User", back_populates="requests")
    files = relationship("File", back_populates="request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Request(request_number='{self.request_number}', title='{self.request_title}')>"

    @classmethod
    def generate_request_number(cls) -> str:
        """Generate unique request number"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"REQ-{timestamp}"

    @classmethod
    def generate_unique_code(cls) -> str:
        """Generate unique identification code"""
        return str(uuid.uuid4()).replace("-", "").upper()[:12]
