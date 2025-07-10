import os
import sys
sys.path.append('/opt/cmsvs')

from sqlalchemy import create_engine, text
from app.config import get_settings

def run_migration():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Create notification enums
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE notificationtype AS ENUM (
                    'REQUEST_STATUS_CHANGED',
                    'REQUEST_CREATED', 
                    'REQUEST_UPDATED',
                    'REQUEST_ARCHIVED',
                    'REQUEST_DELETED',
                    'ADMIN_MESSAGE',
                    'SYSTEM_ANNOUNCEMENT'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE notificationpriority AS ENUM (
                    'LOW',
                    'NORMAL',
                    'HIGH', 
                    'URGENT'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # Create notifications table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                type notificationtype NOT NULL,
                priority notificationpriority NOT NULL DEFAULT 'NORMAL',
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                action_url VARCHAR(500),
                request_id INTEGER REFERENCES requests(id),
                related_user_id INTEGER REFERENCES users(id),
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                is_sent BOOLEAN NOT NULL DEFAULT FALSE,
                sent_at TIMESTAMP WITH TIME ZONE,
                read_at TIMESTAMP WITH TIME ZONE,
                extra_data JSON,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # Create push_subscriptions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                endpoint VARCHAR(500) NOT NULL,
                p256dh_key VARCHAR(255) NOT NULL,
                auth_key VARCHAR(255) NOT NULL,
                user_agent VARCHAR(500),
                device_name VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # Create notification_preferences table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) UNIQUE,
                push_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                in_app_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                email_notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                request_status_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                request_updates_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                admin_message_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                system_announcement_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                quiet_hours_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                quiet_hours_start VARCHAR(5),
                quiet_hours_end VARCHAR(5),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_push_subscriptions_user_id ON push_subscriptions(user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_push_subscriptions_is_active ON push_subscriptions(is_active);"))
        
        conn.commit()
        print("Database migration completed successfully!")

if __name__ == "__main__":
    run_migration()
