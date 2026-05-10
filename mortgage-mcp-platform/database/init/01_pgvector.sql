-- Runs on first PostgreSQL container init (docker-entrypoint-initdb.d)
-- Application also ensures extension via Alembic and startup scripts.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
