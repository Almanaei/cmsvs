#!/bin/bash
# Database initialization script with security hardening

set -e

echo "🔧 Initializing CMSVS database with security hardening..."

# Create additional databases if needed
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";

    -- Create additional schemas if needed
    CREATE SCHEMA IF NOT EXISTS analytics;
    CREATE SCHEMA IF NOT EXISTS audit;

    -- Security: Revoke public schema permissions from public role
    REVOKE CREATE ON SCHEMA public FROM PUBLIC;
    REVOKE ALL ON DATABASE $POSTGRES_DB FROM PUBLIC;

    -- Grant specific permissions to application user
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
    GRANT USAGE, CREATE ON SCHEMA public TO $POSTGRES_USER;
    GRANT USAGE ON SCHEMA analytics TO $POSTGRES_USER;
    GRANT USAGE ON SCHEMA audit TO $POSTGRES_USER;

    -- Set connection limits for application user
    ALTER USER $POSTGRES_USER CONNECTION LIMIT 50;

    -- Create read-only user for monitoring/backup
    CREATE USER cmsvs_readonly WITH PASSWORD '${POSTGRES_READONLY_PASSWORD:-readonly_secure_password}';
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO cmsvs_readonly;
    GRANT USAGE ON SCHEMA public TO cmsvs_readonly;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO cmsvs_readonly;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO cmsvs_readonly;
    ALTER USER cmsvs_readonly CONNECTION LIMIT 5;

    -- Security settings
    ALTER DATABASE $POSTGRES_DB SET log_statement = 'ddl';
    ALTER DATABASE $POSTGRES_DB SET log_min_duration_statement = 1000;

    -- Create audit table for security monitoring
    CREATE TABLE IF NOT EXISTS audit.connection_log (
        id SERIAL PRIMARY KEY,
        username TEXT,
        database_name TEXT,
        client_addr INET,
        connection_time TIMESTAMP DEFAULT NOW(),
        disconnection_time TIMESTAMP,
        session_duration INTERVAL
    );

    -- Grant permissions on audit schema
    GRANT INSERT, SELECT ON audit.connection_log TO $POSTGRES_USER;
    GRANT USAGE ON SEQUENCE audit.connection_log_id_seq TO $POSTGRES_USER;

    -- Create function to log connections (optional)
    CREATE OR REPLACE FUNCTION audit.log_connection()
    RETURNS VOID AS \$\$
    BEGIN
        INSERT INTO audit.connection_log (username, database_name, client_addr)
        VALUES (current_user, current_database(), inet_client_addr());
    END;
    \$\$ LANGUAGE plpgsql SECURITY DEFINER;

    -- Performance optimization: Create indexes on commonly queried columns
    -- These will be created by the application's migration system

EOSQL

echo "✅ Database initialization completed with security hardening"

echo "✅ Database initialization completed successfully!"
