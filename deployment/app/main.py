from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import os
import logging
import time

from app.config import settings
from app.database import create_tables, get_db, get_pool_status
from app.routes import auth, dashboard, admin, messages, achievements, avatar
from app.routes import settings as settings_routes
from app.services.user_service import UserService
from app.models.user import UserRole
from app.utils.auth import verify_token
from app.middleware.database_monitor import DatabaseMonitorMiddleware, database_health_endpoint
from app.middleware.security import add_security_middleware
from app.services.performance import performance_metrics, db_query_monitor, RequestPerformanceMiddleware

# Import achievement models to ensure they're registered with SQLAlchemy
from app.models import achievement
from app.models import user_avatar  # Import avatar model

# Configure logging based on environment
def setup_logging():
    """Configure logging for production and development"""
    import logging.handlers
    import json
    import sys
    from pathlib import Path

    # Ensure log directory exists
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create formatters
    if settings.log_format == "json":
        # JSON formatter for production
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }

                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                # Add extra fields
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                                 'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                                 'relativeCreated', 'thread', 'threadName', 'processName',
                                 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                        log_entry[key] = value

                return json.dumps(log_entry)

        formatter = JSONFormatter()
    else:
        # Standard formatter for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if settings.log_file:
        try:
            # Ensure the log file exists and is writable
            log_file_path = Path(settings.log_file)
            if not log_file_path.exists():
                log_file_path.touch(mode=0o666, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                settings.log_file,
                maxBytes=settings.log_max_size,
                backupCount=settings.log_backup_count
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)
        except (PermissionError, OSError) as e:
            # If we can't write to the log file, just log to console
            console_handler.setLevel(logging.WARNING)
            root_logger.warning(f"Could not create log file {settings.log_file}: {e}. Logging to console only.")

    # Set specific logger levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if settings.is_production else logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if settings.is_production else logging.INFO)

    return root_logger

logger = setup_logging()

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Add CORS middleware with production-ready configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if not settings.debug else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add Database monitoring middleware
app.add_middleware(DatabaseMonitorMiddleware, log_interval=50)

# Add performance monitoring middleware
app.add_middleware(RequestPerformanceMiddleware)

# Add security middleware for production
add_security_middleware(app)

# Custom static files handler with cache control
class CustomStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        # Add cache control headers based on environment
        if settings.debug:
            # Development: No cache for all files
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        else:
            # Production: Cache for static assets only
            if path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg')):
                response.headers["Cache-Control"] = "public, max-age=31536000"  # 1 year
                response.headers["ETag"] = f'"{hash(path)}"'
            else:
                response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour

        return response

# Mount static files with custom handler
os.makedirs("app/static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)  # Create uploads directory
os.makedirs("uploads/avatars", exist_ok=True)  # Create avatars directory
app.mount("/static/uploads", CustomStaticFiles(directory="uploads"), name="uploads")
app.mount("/static", CustomStaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Add global template variables
templates.env.globals["cache_bust"] = str(int(time.time()))

# Add simple avatar URL function for templates
def get_avatar_url_simple(user_id: int, full_name: str) -> str:
    """Simple template function to generate avatar URL without database access"""
    from app.services.avatar_service import AvatarService
    return AvatarService.generate_default_avatar_url(user_id, full_name or "User")

templates.env.globals['get_avatar_url_simple'] = get_avatar_url_simple

# Security
security = HTTPBearer(auto_error=False)


async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    """Get current user from cookie"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    # Remove 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    payload = verify_token(token)
    if not payload:
        return None
    
    username = payload.get("sub")
    if not username:
        return None
    
    user = UserService.get_user_by_username(db, username)
    return user


# Include routers
app.include_router(auth.router, tags=["authentication"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(admin.router, tags=["admin"])
app.include_router(messages.router, prefix="", tags=["messages"])
app.include_router(achievements.router, prefix="", tags=["achievements"])
app.include_router(avatar.router, prefix="/avatar", tags=["avatar"])
app.include_router(settings_routes.router, prefix="", tags=["settings"])


@app.on_event("startup")
async def startup_event():
    """Initialize application"""
    logger.info("Starting CMSVS Internal System...")
    
    # Create database tables
    create_tables()
    logger.info("Database tables created/verified")

    # Set up database query monitoring
    from app.database import engine
    db_query_monitor.setup_query_monitoring(engine)
    logger.info("Database query monitoring enabled")

    # Create avatar tables
    from app.models.user_avatar import UserAvatar
    from app.database import engine
    UserAvatar.metadata.create_all(bind=engine)
    logger.info("Avatar tables created/verified")
    
    # Create default admin user if it doesn't exist
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        admin_user = UserService.get_user_by_email(db, settings.admin_email)
        if not admin_user:
            UserService.create_user(
                db=db,
                username="admin",
                email=settings.admin_email,
                full_name="System Administrator",
                password=settings.admin_password,
                role=UserRole.ADMIN
            )
            logger.info("Default admin user created")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
    finally:
        db.close()
    
    logger.info("Application startup complete")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    """Root endpoint - redirect to appropriate dashboard"""
    current_user = await get_current_user_from_cookie(request, db)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    if current_user.role == UserRole.ADMIN:
        return RedirectResponse(url="/admin/dashboard")
    else:
        return RedirectResponse(url="/dashboard")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.app_version}











@app.get("/health/database")
async def database_health_check():
    """Database health check endpoint"""
    health_status, status_code = await database_health_endpoint()
    return health_status


@app.get("/metrics")
async def get_metrics():
    """Get comprehensive application metrics"""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics endpoint disabled")

    try:
        from app.services.monitoring import get_comprehensive_metrics
        metrics = get_comprehensive_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        raise HTTPException(status_code=500, detail="Error collecting metrics")


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all system components"""
    try:
        from app.services.monitoring import health_checker
        health_status = health_checker.run_all_checks()

        # Return appropriate HTTP status code
        if health_status["status"] == "fail":
            status_code = 503  # Service Unavailable
        elif health_status["status"] == "warn":
            status_code = 200  # OK but with warnings
        else:
            status_code = 200  # OK

        return JSONResponse(
            content=health_status,
            status_code=status_code
        )
    except Exception as e:
        logger.error(f"Error in detailed health check: {e}")
        return JSONResponse(
            content={"status": "fail", "error": str(e)},
            status_code=503
        )


@app.get("/performance")
async def get_performance_metrics():
    """Get application performance metrics"""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Performance metrics endpoint disabled")

    try:
        metrics = performance_metrics.get_performance_summary()
        return metrics
    except Exception as e:
        logger.error(f"Error collecting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Error collecting performance metrics")


@app.get("/performance/database")
async def get_database_performance(db: Session = Depends(get_db)):
    """Get database performance statistics"""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Database performance endpoint disabled")

    try:
        from app.services.performance import performance_optimizer
        stats = performance_optimizer.get_database_performance_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Error collecting database performance stats: {e}")
        raise HTTPException(status_code=500, detail="Error collecting database performance stats")


@app.post("/performance/optimize")
async def optimize_database_performance(db: Session = Depends(get_db)):
    """Optimize database performance"""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Database optimization endpoint disabled")

    try:
        from app.services.performance import performance_optimizer
        performance_optimizer.optimize_database_queries(db)
        return {"status": "success", "message": "Database optimization completed"}
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        raise HTTPException(status_code=500, detail="Error optimizing database")





@app.get("/health/pool")
async def pool_status():
    """Database pool status endpoint"""
    try:
        pool_info = get_pool_status()
        return {"status": "success", "pool": pool_info}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/test/user-progress", response_class=HTMLResponse)
async def test_user_progress(request: Request, db: Session = Depends(get_db)):
    """Test page for user progress display"""
    current_user = await get_current_user_from_cookie(request, db)

    if not current_user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        "test/user_progress_test.html",
        {
            "request": request,
            "current_user": current_user
        }
    )


@app.get("/achievements/user-progress")
async def get_user_progress_data(request: Request, db: Session = Depends(get_db)):
    """API endpoint for user progress data in bento grid"""
    current_user = await get_current_user_from_cookie(request, db)

    if not current_user:
        return {"error": "Authentication required"}

    try:
        # Import here to avoid circular imports
        from app.services.achievement_service import AchievementService
        from app.services.request_service import RequestService

        # Get user's personal progress
        user_progress = RequestService.get_user_personal_progress(db, current_user.id)

        # Get overall system stats
        all_users_progress = RequestService.get_user_progress_tracking(db)

        # Calculate system-wide metrics
        total_active_users = len([u for u in all_users_progress if u['overall_percentage'] > 0])
        avg_completion_rate = sum(u['overall_percentage'] for u in all_users_progress) / len(all_users_progress) if all_users_progress else 0

        # Get top performers for today
        top_performers = sorted(all_users_progress, key=lambda x: x['time_periods']['daily']['completed'], reverse=True)[:3]

        return {
            "daily_progress": user_progress['time_periods']['daily'] if user_progress else {
                "completed": 0, "target": 10, "remaining": 10, "percentage": 0
            },
            "weekly_progress": user_progress['time_periods']['weekly'] if user_progress else {
                "completed": 0, "target": 50, "remaining": 50, "percentage": 0
            },
            "monthly_progress": user_progress['time_periods']['monthly'] if user_progress else {
                "completed": 0, "target": 200, "remaining": 200, "percentage": 0
            },
            "user_stats": {
                "total_achievements": user_progress['achievements']['total_completed'] if user_progress else 0,
                "global_rank": user_progress.get('user_info', {}).get('status_text', 'غير مصنف') if user_progress else 'غير مصنف',
                "completion_rate": user_progress['achievements']['completion_rate'] if user_progress else 0
            },
            "system_stats": {
                "active_users": total_active_users,
                "avg_completion_rate": round(avg_completion_rate, 1),
                "total_requests": sum(u['achievements']['total_requests'] for u in all_users_progress),
                "total_completed": sum(u['achievements']['total_completed'] for u in all_users_progress)
            },
            "top_performers": [
                {
                    "name": performer['user_info']['full_name'],
                    "initial": performer['user_info']['full_name'][0] if performer['user_info']['full_name'] else 'U',
                    "completed": performer['time_periods']['daily']['completed']
                }
                for performer in top_performers
            ],
            "recent_achievements": user_progress.get('achievements', {}).get('badges', []) if user_progress else []
        }

    except Exception as e:
        print(f"Error fetching user progress data: {e}")
        return {"error": "Failed to fetch data"}

















@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    current_user = await get_current_user_from_cookie(request, get_db().__next__())
    return templates.TemplateResponse(
        "errors/404.html",
        {"request": request, "current_user": current_user},
        status_code=404
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    """Handle 403 errors"""
    current_user = await get_current_user_from_cookie(request, get_db().__next__())
    return templates.TemplateResponse(
        "errors/403.html",
        {"request": request, "current_user": current_user},
        status_code=403
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors"""
    current_user = await get_current_user_from_cookie(request, get_db().__next__())
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request, "current_user": current_user},
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
