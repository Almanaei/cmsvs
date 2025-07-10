#!/usr/bin/env python3
"""
Create notification tables manually for CMSVS
This script creates the notification and push subscription tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models.notification import Notification, PushSubscription, NotificationPreference
from app.models.user import User
from app.models.request import Request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_notification_tables():
    """Create notification tables"""
    try:
        logger.info("Creating notification tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Notification tables created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating notification tables: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🔧 CMSVS Notification Tables Creator")
    print("=" * 40)
    
    if create_notification_tables():
        print("\n✅ All notification tables created successfully!")
        print("\n📝 Tables created:")
        print("- notifications")
        print("- push_subscriptions") 
        print("- notification_preferences")
    else:
        print("\n❌ Failed to create notification tables")
        sys.exit(1)
