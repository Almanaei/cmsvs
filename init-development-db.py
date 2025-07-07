#!/usr/bin/env python3
"""
Initialize the development database with tables and admin user
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def init_database():
    """Initialize the database with tables and admin user"""
    try:
        print("🔧 Initializing development database...")
        
        # Set environment to development
        os.environ['ENVIRONMENT'] = 'development'
        
        from app.database import engine, get_db, Base
        from app.models.user import User, UserRole
        from app.models.request import Request
        from app.models.file import File
        from app.models.activity import Activity
        from app.models.achievement import Achievement
        from app.models.user_avatar import UserAvatar
        from app.services.user_service import UserService
        from sqlalchemy.orm import Session
        
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Create admin user
        print("👤 Creating admin user...")
        db = next(get_db())
        
        try:
            # Check if admin already exists
            existing_admin = db.query(User).filter(User.email == "almananei90@gmail.com").first()
            if existing_admin:
                print("ℹ️  Admin user already exists, skipping creation")
            else:
                admin_user = UserService.create_user(
                    db=db,
                    email="almananei90@gmail.com",
                    password="admin123",
                    full_name="System Administrator",
                    role=UserRole.ADMIN
                )
                print(f"✅ Admin user created successfully!")
                print(f"   Email: almananei90@gmail.com")
                print(f"   Password: admin123")
                print(f"   Role: {admin_user.role.value}")
        
        except Exception as e:
            print(f"⚠️  Admin user creation failed: {e}")
            print("   You can create it manually later through the application")
        
        finally:
            db.close()
        
        print("\n🎉 Database initialization completed!")
        print("\n🌐 You can now access the application at:")
        print("   - Main App: http://localhost:8000")
        print("   - Admin Login: http://localhost:8000/admin/login")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check database connection settings in .env.development")
        print("3. Ensure the database 'cmsvs_dev' exists")
        return False

if __name__ == "__main__":
    print("🚀 CMSVS Development Database Initialization")
    print("=" * 50)
    
    success = init_database()
    
    if success:
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)
