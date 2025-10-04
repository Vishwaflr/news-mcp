-- Create admin user cytrex with full permissions
CREATE ROLE cytrex WITH LOGIN PASSWORD 'Aug2012#' SUPERUSER CREATEDB CREATEROLE;

-- Grant permissions on database
GRANT ALL PRIVILEGES ON DATABASE news_db TO cytrex;

-- Grant permissions on schema
GRANT ALL PRIVILEGES ON SCHEMA public TO cytrex;

-- Grant permissions on all existing tables and sequences
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cytrex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cytrex;

-- Set default permissions for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cytrex;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cytrex;
