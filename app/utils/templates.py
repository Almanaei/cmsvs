"""
Shared template configuration for CMSVS application
Provides a centralized Jinja2Templates instance with all global functions and variables
"""

from fastapi.templating import Jinja2Templates
from datetime import datetime as dt, timezone, timedelta
import time
import logging

logger = logging.getLogger(__name__)

# Create the shared templates instance
templates = Jinja2Templates(directory="app/templates")

# Add global template variables
templates.env.globals["cache_bust"] = str(int(time.time()))

# Add timezone utilities for Bahrain time
def utc_to_bahrain(dt_obj):
    """Convert UTC datetime to Bahrain time (UTC+3)"""
    if dt_obj is None:
        return None
    try:
        # If datetime is naive, assume it's UTC
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        # Convert to Bahrain timezone (UTC+3)
        bahrain_tz = timezone(timedelta(hours=3))
        return dt_obj.astimezone(bahrain_tz)
    except Exception as e:
        logger.error(f"Error converting to Bahrain time: {e}")
        return dt_obj

def now_bahrain():
    """Get current time in Bahrain timezone"""
    bahrain_tz = timezone(timedelta(hours=3))
    return dt.now(bahrain_tz)

def get_now_bahrain():
    """Template-friendly function to get current time in Bahrain timezone"""
    return now_bahrain()

# Add timezone functions to template globals
templates.env.globals["utc_to_bahrain"] = utc_to_bahrain
templates.env.globals["now_bahrain"] = get_now_bahrain

# Add simple avatar URL function for templates
def get_avatar_url_simple(user_id: int, full_name: str) -> str:
    """Simple template function to generate avatar URL without database access"""
    from app.services.avatar_service import AvatarService
    return AvatarService.generate_default_avatar_url(user_id, full_name or "User")

templates.env.globals['get_avatar_url_simple'] = get_avatar_url_simple
