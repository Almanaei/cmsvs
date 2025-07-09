#!/usr/bin/env python3
"""
Database initialization script for CMSVS Internal System
Run this script to create database tables and default admin user
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import create_tables, SessionLocal
from app.services.user_service import UserService
from app.models.user import UserRole
from app.config import settings

def init_database():
    """Initialize database with tables and default admin user"""
    print("🔧 Initializing CMSVS Database...")
    print("=" * 50)
    
    try:
        # Create database tables
        print("📋 Creating database tables...")
        create_tables()
        print("✅ Database tables created successfully")
        
        # Create default admin user
        db = SessionLocal()
        try:
            print("👤 Creating default admin user...")
            
            # Check if admin user already exists
            admin_user = UserService.get_user_by_email(db, settings.admin_email)
            if admin_user:
                print("⚠️  Admin user already exists")
                print(f"   Email: {admin_user.email}")
                print(f"   Username: {admin_user.username}")
            else:
                # Create admin user
                admin_user = UserService.create_user(
                    db=db,
                    username="admin",
                    email=settings.admin_email,
                    full_name="System Administrator",
                    password=settings.admin_password,
                    role=UserRole.ADMIN
                )
                print("✅ Default admin user created successfully")
                print(f"   Email: {admin_user.email}")
                print(f"   Username: {admin_user.username}")
                print(f"   Password: {settings.admin_password}")
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            return False
        finally:
            db.close()
        
        print("=" * 50)
        print("🎉 Database initialization completed successfully!")
        print()
        print("📝 Next steps:")
        print("1. Start the application: python run.py")
        print("2. Open browser: http://localhost:8000")
        print("3. Login with admin credentials")
        print("4. Change default admin password")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print()
        print("🔍 Troubleshooting:")
        print("1. Check if PostgreSQL is running")
        print("2. Verify database connection in .env file")
        print("3. Ensure database exists and user has permissions")
        print()
        return False

def main():
    """Main function"""
    print("CMSVS Internal System - Database Initialization")
    print("=" * 50)
    print(f"Database URL: {settings.database_url}")
    print(f"Admin Email: {settings.admin_email}")
    print("=" * 50)
    print()
    
    success = init_database()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
