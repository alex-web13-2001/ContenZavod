-- ContenZavod: PostgreSQL initialization
-- This script runs on first database creation

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application role (non-superuser, for RLS enforcement)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cz_app') THEN
        CREATE ROLE cz_app LOGIN PASSWORD 'cz_app_password';
    END IF;
END
$$;

-- Grant permissions
GRANT CONNECT ON DATABASE contenzavod TO cz_app;
GRANT USAGE ON SCHEMA public TO cz_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cz_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cz_app;

-- Note: RLS policies are created by Alembic migrations along with tables.
-- This file only handles extensions and roles that need to exist before tables.
