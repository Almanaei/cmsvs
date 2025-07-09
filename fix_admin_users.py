#!/usr/bin/env python3
"""
Script to fix existing admin users by setting them as active and approved.
This ensures admin users can log in directly without approval.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import SessionLocal, engine
from app.models.user import User, UserRole, UserStatus
from sqlalchemy.orm import Session


def fix_admin_users():
    """Update all admin users to be active and approved"""
    db = SessionLocal()
    try:
        # Find all admin users
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
        
        if not admin_users:
            print("❌ No admin users found in the database")
            return
        
        print(f"🔍 Found {len(admin_users)} admin user(s)")
        
        updated_count = 0
        for admin_user in admin_users:
            needs_update = False
            
            # Check if user needs to be activated
            if not admin_user.is_active:
                admin_user.is_active = True
                needs_update = True
                print(f"✅ Activated admin user: {admin_user.username}")
            
            # Check if user needs to be approved
            if admin_user.approval_status != UserStatus.APPROVED:
                admin_user.approval_status = UserStatus.APPROVED
                needs_update = True
                print(f"✅ Approved admin user: {admin_user.username}")
            
            if needs_update:
                updated_count += 1
            else:
                print(f"ℹ️  Admin user {admin_user.username} is already active and approved")
        
        if updated_count > 0:
            db.commit()
            print(f"\n🎉 Successfully updated {updated_count} admin user(s)")
        else:
            print("\n✨ All admin users are already properly configured")
            
    except Exception as e:
        print(f"❌ Error updating admin users: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🔧 Fixing admin users...")
    fix_admin_users()
    print("✅ Done!")
