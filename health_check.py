#!/usr/bin/env python3
"""
Health check script for CMSVS Internal System
Run this script to verify the system is working properly
"""

import sys
import requests
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_application_running(url="http://localhost:8000"):
    """Check if the application is running"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - application not running"
    except requests.exceptions.Timeout:
        return False, "Request timeout"
    except Exception as e:
        return False, str(e)

def check_database_connection():
    """Check database connection"""
    try:
        from app.database import SessionLocal
        from app.models.user import User
        
        db = SessionLocal()
        try:
            # Try to query the database
            user_count = db.query(User).count()
            return True, f"Connected - {user_count} users in database"
        finally:
            db.close()
    except Exception as e:
        return False, str(e)

def check_admin_user():
    """Check if admin user exists"""
    try:
        from app.database import SessionLocal
        from app.services.user_service import UserService
        from app.config import settings
        
        db = SessionLocal()
        try:
            admin_user = UserService.get_user_by_email(db, settings.admin_email)
            if admin_user:
                return True, f"Admin user exists: {admin_user.username}"
            else:
                return False, "Admin user not found"
        finally:
            db.close()
    except Exception as e:
        return False, str(e)

def check_file_permissions():
    """Check file and directory permissions"""
    try:
        from app.config import settings
        import os
        
        # Check upload directory
        upload_dir = settings.upload_directory
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
        
        # Test write permissions
        test_file = os.path.join(upload_dir, "test_write.tmp")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        
        return True, f"Upload directory writable: {upload_dir}"
    except Exception as e:
        return False, str(e)

def check_login_page(url="http://localhost:8000"):
    """Check if login page is accessible"""
    try:
        response = requests.get(f"{url}/login", timeout=5)
        if response.status_code == 200:
            if "تسجيل الدخول" in response.text or "login" in response.text.lower():
                return True, "Login page accessible"
            else:
                return False, "Login page content unexpected"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    """Main health check function"""
    print("=" * 60)
    print("🏥 CMSVS Internal System - Health Check")
    print("=" * 60)
    print()
    
    checks = [
        ("Application Running", lambda: check_application_running()),
        ("Database Connection", check_database_connection),
        ("Admin User", check_admin_user),
        ("File Permissions", check_file_permissions),
        ("Login Page", lambda: check_login_page()),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"🔍 Checking {check_name}...")
        try:
            success, message = check_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status} - {message}")
            results.append((check_name, success, message))
        except Exception as e:
            print(f"   ❌ ERROR - {str(e)}")
            results.append((check_name, False, str(e)))
        print()
    
    # Summary
    print("=" * 60)
    print("📊 HEALTH CHECK SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for check_name, success, message in results:
        status = "✅ HEALTHY" if success else "❌ UNHEALTHY"
        print(f"{status} - {check_name}")
    
    print(f"\nOverall Status: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 System is healthy and ready to use!")
        print("\n🌐 Access URLs:")
        print("   Application: http://localhost:8000")
        print("   Login: http://localhost:8000/login")
        print("   API Docs: http://localhost:8000/docs")
    else:
        print(f"\n⚠️  {total - passed} issue(s) found. Please address them before using the system.")
        
        print("\n🔧 Troubleshooting:")
        for check_name, success, message in results:
            if not success:
                print(f"\n❌ {check_name}:")
                print(f"   Issue: {message}")
                
                # Provide specific troubleshooting advice
                if "Connection refused" in message:
                    print("   Solution: Start the application with 'python run.py'")
                elif "database" in check_name.lower():
                    print("   Solution: Check PostgreSQL is running and .env configuration")
                elif "admin user" in check_name.lower():
                    print("   Solution: Run 'python init_db.py' to create admin user")
                elif "permission" in check_name.lower():
                    print("   Solution: Check file/directory permissions")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
