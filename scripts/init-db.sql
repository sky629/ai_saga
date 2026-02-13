-- Initialize databases
-- Note: Main database 'ai_saga' is created automatically via POSTGRES_DB environment variable

-- Create test database
CREATE DATABASE ai_saga_test;
GRANT ALL PRIVILEGES ON DATABASE ai_saga_test TO postgres;

-- Enable pgvector extension for main database
\c ai_saga;
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pgvector extension for test database
\c ai_saga_test;
CREATE EXTENSION IF NOT EXISTS vector;
