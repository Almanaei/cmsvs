#!/usr/bin/env python3
"""
Run CMSVS application with local PostgreSQL database
This script sets up the database and starts the application
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_postgresql():
    """Check if PostgreSQL is running locally"""
    try:
        import psycopg2
        import getpass

        # First try without password (for trust authentication)
        try:
            conn = psycopg2.connect(
                host="localhost",
                port="5432",
                user="postgres",
                database="postgres"
            )
            conn.close()
            print("✅ PostgreSQL is running locally")
            return True
        except psycopg2.OperationalError as e:
            if "no password supplied" in str(e) or "password authentication failed" in str(e):
                # Password is required, prompt for it
                print("🔐 PostgreSQL requires authentication")
                password = getpass.getpass("Enter PostgreSQL password for user 'postgres': ")

                conn = psycopg2.connect(
                    host="localhost",
                    port="5432",
                    user="postgres",
                    password=password,
                    database="postgres"
                )
                conn.close()
                print("✅ PostgreSQL is running locally")

                # Store password for later use
                os.environ['POSTGRES_ADMIN_PASSWORD'] = password
                return True
            else:
                raise e

    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running on localhost:5432")
        print("2. Check your PostgreSQL password")
        print("3. Verify PostgreSQL allows local connections")
        return False

def setup_database():
    """Set up the development database"""
    try:
        print("🔧 Setting up development database...")

        # Try to run the SQL setup script
        sql_file = project_root / "setup-local-db.sql"
        if sql_file.exists():
            print("📋 Running database setup script...")

            # Prepare psql command
            cmd = ["psql", "-h", "localhost", "-U", "postgres", "-f", str(sql_file)]

            # Set password environment variable if available
            env = os.environ.copy()
            if 'POSTGRES_ADMIN_PASSWORD' in os.environ:
                env['PGPASSWORD'] = os.environ['POSTGRES_ADMIN_PASSWORD']

            result = subprocess.run(cmd, capture_output=True, text=True, env=env)

            if result.returncode == 0:
                print("✅ Database setup completed successfully!")
                return True
            else:
                print(f"⚠️  Database setup had issues: {result.stderr}")
                print("Continuing anyway - database might already exist")
                return True
        else:
            print("⚠️  Database setup script not found, skipping...")
            return True

    except Exception as e:
        print(f"⚠️  Database setup failed: {e}")
        print("You may need to set up the database manually")
        return True  # Continue anyway

def init_application_database():
    """Initialize application tables and admin user"""
    try:
        print("🔧 Initializing application database...")
        
        # Set environment to use local config
        os.environ['ENV_FILE'] = '.env.local'
        
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
                print("ℹ️  Admin user already exists")
                print(f"   Email: almananei90@gmail.com")
                print(f"   Role: {existing_admin.role.value}")
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
        
        return True
        
    except Exception as e:
        print(f"❌ Application database initialization failed: {e}")
        return False

def start_application():
    """Start the FastAPI application"""
    try:
        print("🚀 Starting CMSVS application...")
        print("=" * 60)
        
        # Set environment to use local config
        os.environ['ENV_FILE'] = '.env.local'
        
        import uvicorn
        from app.config import settings
        
        print(f"📋 Application: {settings.app_name}")
        print(f"📊 Version: {settings.app_version}")
        print(f"🔧 Debug Mode: {settings.debug}")
        print(f"🌐 Host: localhost")
        print(f"🔌 Port: 8000")
        print("=" * 60)
        print()
        print("📝 Default Admin Credentials:")
        print(f"   Email: almananei90@gmail.com")
        print(f"   Password: admin123")
        print()
        print("🌍 Access URLs:")
        print("   Main App: http://localhost:8000")
        print("   Admin Login: http://localhost:8000/admin/login")
        print("   API Docs: http://localhost:8000/docs")
        print()
        print("🧪 Test the Logger Fix:")
        print("   1. Login as admin")
        print("   2. Go to 'New Request' page")
        print("   3. Try creating a request")
        print("   4. The logger error should be resolved!")
        print("=" * 60)
        print()
        
        uvicorn.run(
            "app.main:app",
            host="localhost",
            port=8000,
            reload=True,
            log_level="debug",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        return False
    
    return True

def main():
    """Main function"""
    print("🚀 CMSVS Local Development Setup")
    print("=" * 50)
    
    # Step 1: Check PostgreSQL
    print("\n📋 Step 1: Checking PostgreSQL...")
    if not check_postgresql():
        print("\n❌ Setup failed. Please start PostgreSQL and try again.")
        return False
    
    # Step 2: Setup database
    print("\n📋 Step 2: Setting up database...")
    if not setup_database():
        print("\n❌ Database setup failed.")
        return False
    
    # Step 3: Initialize application database
    print("\n📋 Step 3: Initializing application...")
    if not init_application_database():
        print("\n❌ Application initialization failed.")
        return False
    
    # Step 4: Start application
    print("\n📋 Step 4: Starting application...")
    start_application()
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
