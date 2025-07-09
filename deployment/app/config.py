from pydantic_settings import BaseSettings
from typing import Optional, List
import os
import secrets
import logging


class Settings(BaseSettings):
    # Environment
    environment: str = "development"

    # Database
    database_url: str = "postgresql://username:password@localhost:5432/cmsvs_db"
    db_password: Optional[str] = None  # For Docker environment
    redis_password: Optional[str] = None  # For Docker environment

    # Database Pool Settings
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_timeout: int = 60
    db_pool_recycle: int = 3600

    # Security
    secret_key: str = "your-secret-key-here-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # File Upload
    max_file_size: int = 10485760  # 10MB
    allowed_file_types: str = "pdf,doc,docx,txt,jpg,jpeg,png,gif"
    upload_directory: str = "uploads"

    # Application
    app_name: str = "CMSVS Internal System"
    app_version: str = "1.0.0"
    debug: bool = True

    # Admin
    admin_email: str = "admin@company.com"
    admin_password: str = "admin123"

    # Network Configuration
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # SSL/TLS Configuration
    force_https: bool = False
    secure_cookies: bool = False
    hsts_max_age: int = 31536000

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_max_size: int = 10485760  # 10MB
    log_backup_count: int = 5
    log_format: str = "standard"  # standard or json

    # Rate Limiting
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    rate_limit_burst: int = 20

    # Session Configuration
    session_timeout: int = 1800  # 30 minutes
    remember_me_duration: int = 2592000  # 30 days

    # Performance Configuration
    enable_gzip: bool = True
    static_file_cache: int = 3600
    api_cache_ttl: int = 300

    # Monitoring
    health_check_enabled: bool = True
    metrics_enabled: bool = False
    prometheus_port: int = 9090

    # Email Configuration
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True

    # Backup Configuration
    backup_enabled: bool = False
    backup_schedule: str = "0 2 * * *"
    backup_retention_days: int = 30
    backup_location: str = "backups"

    # Worker Configuration
    worker_processes: int = 1
    worker_connections: int = 1000
    worker_timeout: int = 30

    # Database Backup
    db_backup_enabled: bool = False
    db_backup_schedule: str = "0 1 * * *"
    db_backup_retention_days: int = 30
    db_backup_location: str = "db_backups"

    # Security Headers
    security_headers_enabled: bool = True
    content_security_policy: str = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; connect-src 'self'"
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    referrer_policy: str = "strict-origin-when-cross-origin"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def allowed_file_types_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_file_types.split(",")]

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [host.strip() for host in self.allowed_hosts.split(",")]

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    def validate_production_settings(self) -> List[str]:
        """Validate critical production settings and return list of issues"""
        issues = []

        if self.is_production:
            # Check secret key
            if self.secret_key == "your-secret-key-here-change-this-in-production":
                issues.append("SECRET_KEY must be changed for production")
            elif len(self.secret_key) < 32:
                issues.append("SECRET_KEY should be at least 32 characters long")

            # Check admin password
            if self.admin_password in ["admin123", "password", "123456"]:
                issues.append("ADMIN_PASSWORD must be changed from default value")

            # Check debug mode
            if self.debug:
                issues.append("DEBUG must be False in production")

            # Check database URL
            if "localhost" in self.database_url:
                issues.append("DATABASE_URL should not use localhost in production")

            # Check HTTPS (temporarily disabled for HTTP-only deployment)
            # if not self.force_https:
            #     issues.append("FORCE_HTTPS should be True in production")

        return issues

    def generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)


# Determine environment file
env_file = ".env"
if os.getenv("ENVIRONMENT") == "production":
    env_file = ".env.production"
elif os.path.exists(".env.local"):
    env_file = ".env.local"

# Create settings instance with appropriate env file
class ProductionSettings(Settings):
    class Config:
        env_file = env_file
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables

settings = ProductionSettings()

# Validate production settings
if settings.is_production:
    issues = settings.validate_production_settings()
    if issues:
        logger = logging.getLogger(__name__)
        logger.error("Production configuration issues found:")
        for issue in issues:
            logger.error(f"  - {issue}")
        raise ValueError(f"Production configuration issues: {', '.join(issues)}")

# Ensure directories exist
os.makedirs(settings.upload_directory, exist_ok=True)
os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
if settings.backup_enabled:
    os.makedirs(settings.backup_location, exist_ok=True)
if settings.db_backup_enabled:
    os.makedirs(settings.db_backup_location, exist_ok=True)
