from fastapi import Request
from typing import Optional


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request headers"""
    # Check for forwarded headers first (for reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Check for Cloudflare connecting IP
    cf_connecting_ip = request.headers.get("CF-Connecting-IP")
    if cf_connecting_ip:
        return cf_connecting_ip.strip()
    
    # Fall back to client host
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request headers"""
    return request.headers.get("User-Agent")


def log_user_activity(
    db,
    user_id: int,
    activity_type: str,
    description: str,
    request: Request,
    details: Optional[dict] = None
):
    """Helper function to log user activity with IP and user agent"""
    from app.services.activity_service import ActivityService

    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    return ActivityService.log_activity(
        db=db,
        user_id=user_id,
        activity_type=activity_type,
        description=description,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_cross_user_activity(
    db,
    request_owner_id: int,
    accessing_user_id: int,
    accessing_user_name: str,
    activity_type: str,
    description: str,
    request: Request,
    details: Optional[dict] = None
):
    """Helper function to log when a user accesses another user's request"""
    from app.services.activity_service import ActivityService

    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Add accessing user info to details
    if details is None:
        details = {}

    details.update({
        "accessing_user_id": accessing_user_id,
        "accessing_user_name": accessing_user_name,
        "cross_user_access": True
    })

    return ActivityService.log_activity(
        db=db,
        user_id=request_owner_id,  # Log to the request owner's activity
        activity_type=activity_type,
        description=description,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
