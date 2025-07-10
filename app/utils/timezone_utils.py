"""
Timezone utilities for CMSVS application
Handles conversion between UTC and Bahrain timezone (UTC+3)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Bahrain timezone (UTC+3)
BAHRAIN_TZ = timezone(timedelta(hours=3))

def utc_to_bahrain(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert UTC datetime to Bahrain time (UTC+3)
    
    Args:
        dt: UTC datetime object (timezone-aware or naive)
        
    Returns:
        Datetime object in Bahrain timezone or None if input is None
    """
    if dt is None:
        return None
    
    try:
        # If datetime is naive, assume it's UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to Bahrain timezone
        bahrain_time = dt.astimezone(BAHRAIN_TZ)
        return bahrain_time
        
    except Exception as e:
        logger.error(f"Error converting UTC to Bahrain time: {e}")
        return dt  # Return original datetime if conversion fails


def now_bahrain() -> datetime:
    """
    Get current time in Bahrain timezone
    
    Returns:
        Current datetime in Bahrain timezone
    """
    return datetime.now(BAHRAIN_TZ)


def format_bahrain_datetime(dt: Optional[datetime], format_type: str = "full") -> str:
    """
    Format datetime in Bahrain timezone with Arabic-friendly format
    
    Args:
        dt: Datetime object to format
        format_type: Type of format ("full", "date", "time", "short")
        
    Returns:
        Formatted datetime string in Arabic
    """
    if dt is None:
        return "غير محدد"
    
    try:
        # Convert to Bahrain time
        bahrain_dt = utc_to_bahrain(dt)
        if bahrain_dt is None:
            return "غير محدد"
        
        if format_type == "full":
            return bahrain_dt.strftime('%Y-%m-%d في %H:%M:%S')
        elif format_type == "date":
            return bahrain_dt.strftime('%Y-%m-%d')
        elif format_type == "time":
            return bahrain_dt.strftime('%H:%M:%S')
        elif format_type == "short":
            return bahrain_dt.strftime('%Y-%m-%d في %H:%M')
        else:
            return bahrain_dt.strftime('%Y-%m-%d في %H:%M:%S')
            
    except Exception as e:
        logger.error(f"Error formatting Bahrain datetime: {e}")
        return "خطأ في التنسيق"


def get_time_ago_arabic(dt: Optional[datetime], reference_time: Optional[datetime] = None) -> str:
    """
    Get time difference in Arabic (relative to Bahrain time)
    
    Args:
        dt: Datetime to compare
        reference_time: Reference time (defaults to current Bahrain time)
        
    Returns:
        Time difference string in Arabic
    """
    if dt is None:
        return "غير محدد"
    
    try:
        if reference_time is None:
            reference_time = now_bahrain()
        else:
            reference_time = utc_to_bahrain(reference_time)
        
        bahrain_dt = utc_to_bahrain(dt)
        if bahrain_dt is None or reference_time is None:
            return "غير محدد"
        
        # Calculate time difference
        time_diff = (reference_time - bahrain_dt).total_seconds()
        
        if time_diff < 0:
            # Future time
            time_diff = abs(time_diff)
            if time_diff < 60:
                return "بعد ثوانٍ قليلة"
            elif time_diff < 3600:
                minutes = int(time_diff / 60)
                return f"بعد {minutes} دقيقة"
            elif time_diff < 86400:
                hours = int(time_diff / 3600)
                return f"بعد {hours} ساعة"
            else:
                days = int(time_diff / 86400)
                return f"بعد {days} يوم"
        else:
            # Past time
            if time_diff < 60:
                return "منذ ثوانٍ قليلة"
            elif time_diff < 3600:
                minutes = int(time_diff / 60)
                return f"منذ {minutes} دقيقة"
            elif time_diff < 86400:
                hours = int(time_diff / 3600)
                return f"منذ {hours} ساعة"
            else:
                days = int(time_diff / 86400)
                return f"منذ {days} يوم"
                
    except Exception as e:
        logger.error(f"Error calculating time ago in Arabic: {e}")
        return "غير محدد"


def create_bahrain_datetime(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    """
    Create a datetime object in Bahrain timezone
    
    Args:
        year, month, day, hour, minute, second: Date/time components
        
    Returns:
        Datetime object in Bahrain timezone
    """
    return datetime(year, month, day, hour, minute, second, tzinfo=BAHRAIN_TZ)


def is_same_day_bahrain(dt1: Optional[datetime], dt2: Optional[datetime]) -> bool:
    """
    Check if two datetimes are on the same day in Bahrain timezone
    
    Args:
        dt1, dt2: Datetime objects to compare
        
    Returns:
        True if same day in Bahrain timezone, False otherwise
    """
    if dt1 is None or dt2 is None:
        return False
    
    try:
        bahrain_dt1 = utc_to_bahrain(dt1)
        bahrain_dt2 = utc_to_bahrain(dt2)
        
        if bahrain_dt1 is None or bahrain_dt2 is None:
            return False
        
        return (bahrain_dt1.year == bahrain_dt2.year and 
                bahrain_dt1.month == bahrain_dt2.month and 
                bahrain_dt1.day == bahrain_dt2.day)
                
    except Exception as e:
        logger.error(f"Error comparing dates in Bahrain timezone: {e}")
        return False


# Template filter functions for Jinja2
def bahrain_datetime_filter(dt: Optional[datetime], format_type: str = "full") -> str:
    """Jinja2 filter for formatting datetime in Bahrain timezone"""
    return format_bahrain_datetime(dt, format_type)


def bahrain_time_ago_filter(dt: Optional[datetime]) -> str:
    """Jinja2 filter for time ago in Arabic (Bahrain timezone)"""
    return get_time_ago_arabic(dt)
