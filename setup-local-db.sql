-- CMSVS Local Development Database Setup
-- Run this script in your PostgreSQL to create the development database

-- Create database user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cmsvs_user') THEN
        CREATE USER cmsvs_user WITH PASSWORD 'cmsvs_password123';
    END IF;
END
$$;

-- Create development database if it doesn't exist
SELECT 'CREATE DATABASE cmsvs_dev OWNER cmsvs_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cmsvs_dev')\gexec

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON DATABASE cmsvs_dev TO cmsvs_user;

-- Connect to the new database and grant schema privileges
\c cmsvs_dev

-- Grant privileges on the public schema
GRANT ALL ON SCHEMA public TO cmsvs_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cmsvs_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cmsvs_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cmsvs_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cmsvs_user;

-- Display success message
\echo 'Database setup completed successfully!'
\echo 'Database: cmsvs_dev'
\echo 'User: cmsvs_user'
\echo 'Password: cmsvs_password123'
