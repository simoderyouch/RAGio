-- PostgreSQL Database Initialization Script
-- This script runs when the PostgreSQL container starts for the first time

-- Create database if it doesn't exist
-- (PostgreSQL creates the database automatically based on POSTGRES_DB environment variable)

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema for better organization
CREATE SCHEMA IF NOT EXISTS public;

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance
-- (These will be created by SQLAlchemy models, but we can add additional ones here)

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE hcp TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL database initialized successfully';
    RAISE NOTICE 'Database: %', current_database();
    RAISE NOTICE 'User: %', current_user;
    RAISE NOTICE 'Timezone: %', current_setting('timezone');
END $$;
