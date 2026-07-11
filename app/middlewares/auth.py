"""
Authentication Middleware Module

This module provides middleware for authentication and authorization.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.utils.auth import decode_access_token
from app.models.user import UserRole
from typing import Optional


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT authentication.
    
    This middleware checks for valid JWT tokens in the Authorization header
    for protected routes.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process incoming request and validate JWT token.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            Response: HTTP response
        """
        # Skip authentication for public routes
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            return await call_next(request)
        
        if request.url.path.startswith("/api/v1/auth"):
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authorization header missing"}
            )
        
        # Extract and validate token
        try:
            token = auth_header.replace("Bearer ", "")
            payload = decode_access_token(token)
            
            if not payload:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or expired token"}
                )
            
            # Add user info to request state
            request.state.user_id = payload.get("sub")
            request.state.user_role = payload.get("role")
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Authentication error: {str(e)}"}
            )
        
        return await call_next(request)


class RoleMiddleware(BaseHTTPMiddleware):
    """
    Middleware for role-based access control.
    
    This middleware checks if the user has the required role for specific routes.
    """
    
    def __init__(self, app, required_role: UserRole = UserRole.USER):
        """
        Initialize role middleware.
        
        Args:
            app: ASGI application
            required_role: Required role for access
        """
        super().__init__(app)
        self.required_role = required_role
    
    async def dispatch(self, request: Request, call_next):
        """
        Process incoming request and validate user role.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            Response: HTTP response
        """
        user_role = getattr(request.state, "user_role", None)
        
        if not user_role:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "User not authenticated"}
            )
        
        # Admin has access to everything
        if user_role == UserRole.ADMIN:
            return await call_next(request)
        
        # Check if user has required role
        if user_role != self.required_role:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"Access denied. {self.required_role.value} role required."}
            )
        
        return await call_next(request)
