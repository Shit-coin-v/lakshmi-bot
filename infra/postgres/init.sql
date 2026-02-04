-- Initial PostgreSQL setup
-- This script runs once when the database volume is first created.
-- The database and user are created automatically by the postgres Docker image
-- via POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD environment variables.

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
