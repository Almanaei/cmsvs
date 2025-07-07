#!/usr/bin/env python3
"""
Simple script to run CMSVS with local PostgreSQL
Assumes database is already set up
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main function to run the application"""
    print("🚀 Starting CMSVS with Local PostgreSQL")
    print("=" * 50)
    
    # Set environment to use local config
    os.environ['ENV_FILE'] = '.env.local'
    
    try:
        import uvicorn
        from app.config import settings
        
        print(f"📋 Application: {settings.app_name}")
        print(f"🔧 Debug Mode: {settings.debug}")
        print(f"🌐 Host: localhost")
        print(f"🔌 Port: 8001")
        print("=" * 50)
        print()
        print("📝 Default Admin Credentials:")
        print(f"   Email: almananei90@gmail.com")
        print(f"   Password: admin123")
        print()
        print("🌍 Access URLs:")
        print("   Main App: http://localhost:8001")
        print("   Admin Login: http://localhost:8001/admin/login")
        print("   API Docs: http://localhost:8001/docs")
        print()
        print("🧪 Test the Logger Fix:")
        print("   1. Login as admin")
        print("   2. Go to 'New Request' page")
        print("   3. Try creating a request")
        print("   4. The logger error should be resolved!")
        print("=" * 50)
        print()
        print("Starting application...")
        print()
        
        uvicorn.run(
            "app.main:app",
            host="localhost",
            port=8001,
            reload=True,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Run setup-db-manual.bat first to create database")
        print("3. Check database connection in .env.local")
        return False
    
    return True

if __name__ == "__main__":
    main()
