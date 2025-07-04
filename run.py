#!/usr/bin/env python3
"""
CMSVS Internal System - FastAPI + HTMX Application
Run this script to start the application
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import settings

def main():
    """Main function to run the application"""
    print("=" * 60)
    print("🚀 Starting CMSVS Internal System")
    print("=" * 60)
    print(f"📋 Application: {settings.app_name}")
    print(f"📊 Version: {settings.app_version}")
    print(f"🔧 Debug Mode: {settings.debug}")
    print(f"🌐 Host: 0.0.0.0")
    print(f"🔌 Port: 8000")
    print("=" * 60)
    print()
    print("📝 Default Admin Credentials:")
    print(f"   Username: admin")
    print(f"   Password: {settings.admin_password}")
    print()
    print("🌍 Access URLs:")
    print("   Local: http://localhost:8000")
    print("   Network: http://0.0.0.0:8000")
    print()
    print("📚 API Documentation:")
    print("   Swagger UI: http://localhost:8000/docs")
    print("   ReDoc: http://localhost:8000/redoc")
    print()
    print("⚠️  Important Notes:")
    print("   - Make sure PostgreSQL is running")
    print("   - Update database connection in .env file")
    print("   - Change default admin password after first login")
    print("=" * 60)
    print()

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=settings.debug,
            log_level="info" if not settings.debug else "debug",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
