"""
Security middleware for CMSVS Internal System
Implements security headers, rate limiting, and other security measures
"""

import time
import hashlib
from typing import Dict, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
from collections import defaultdict, deque
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.enabled = settings.rate_limit_enabled
        self.max_requests = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window
        self.burst_limit = settings.rate_limit_burst
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Use X-Forwarded-For if behind proxy, otherwise use client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include user agent for additional uniqueness
        user_agent = request.headers.get("User-Agent", "")
        client_id = hashlib.md5(f"{client_ip}:{user_agent}".encode()).hexdigest()
        
        return client_id
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited"""
        if not self.enabled:
            return False
        
        now = time.time()
        client_requests = self.requests[client_id]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        # Check if client has exceeded rate limit
        if len(client_requests) >= self.max_requests:
            return True
        
        # Add current request
        client_requests.append(now)
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/health/database"] or request.url.path.startswith("/static"):
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        
        if self._is_rate_limited(client_id):
            logger.warning(f"Rate limit exceeded for client {client_id[:8]}... on {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.max_requests} requests per {self.window_seconds} seconds"
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Window": str(self.window_seconds)
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        client_requests = self.requests[client_id]
        remaining = max(0, self.max_requests - len(client_requests))
        
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = settings.security_headers_enabled
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if not self.enabled:
            return response
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": settings.x_content_type_options,
            "X-Frame-Options": settings.x_frame_options,
            "Referrer-Policy": settings.referrer_policy,
            "X-XSS-Protection": "1; mode=block",
            "X-Permitted-Cross-Domain-Policies": "none",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin"
        }
        
        # Add Content Security Policy
        if settings.content_security_policy:
            security_headers["Content-Security-Policy"] = settings.content_security_policy
        
        # Add HSTS header for HTTPS
        if settings.force_https and request.url.scheme == "https":
            security_headers["Strict-Transport-Security"] = f"max-age={settings.hsts_max_age}; includeSubDomains"
        
        # Add security headers to response
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to redirect HTTP to HTTPS in production"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.force_https = settings.force_https
    
    async def dispatch(self, request: Request, call_next):
        if (self.force_https and 
            request.url.scheme == "http" and 
            not request.url.hostname in ["localhost", "127.0.0.1"]):
            
            # Redirect to HTTPS
            https_url = request.url.replace(scheme="https")
            return Response(
                status_code=301,
                headers={"Location": str(https_url)}
            )
        
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests in production"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.log_requests = settings.is_production
    
    async def dispatch(self, request: Request, call_next):
        if not self.log_requests:
            return await call_next(request)
        
        start_time = time.time()
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        user_agent = request.headers.get("User-Agent", "")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log successful requests
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s - "
                f"Client: {client_ip} - "
                f"UA: {user_agent[:50]}..."
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(round(process_time, 3))
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Log errors
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Error: {str(e)} - "
                f"Time: {process_time:.3f}s - "
                f"Client: {client_ip}"
            )
            
            raise


class ContentValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating request content"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.max_content_length = settings.max_file_size
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request entity too large",
                    "message": f"Maximum content length is {self.max_content_length} bytes"
                }
            )
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            # Allow common content types
            allowed_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain"
            ]
            
            if not any(allowed_type in content_type for allowed_type in allowed_types):
                logger.warning(f"Suspicious content type: {content_type} from {request.client.host if request.client else 'unknown'}")
        
        return await call_next(request)


# Utility function to add all security middleware
def add_security_middleware(app):
    """Add all security middleware to the FastAPI app"""
    
    # Add middleware in reverse order (last added is executed first)
    app.add_middleware(ContentValidationMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    logger.info("Security middleware added to application")
