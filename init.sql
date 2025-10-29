-- Title: Init Letta Database

-- Fetch the docker secrets, if they are available.
-- Otherwise fall back to environment variables, or hardwired 'letta'
\set db_user `echo "${POSTGRES_USER:-juan}"`
\set db_password `echo "${POSTGRES_PASSWORD:-juan}"`
\set db_name `echo "${POSTGRES_DB:-juan}"`

CREATE SCHEMA IF NOT EXISTS:"db_name"
    AUTHORIZATION :"db_user";

ALTER DATABASE :"db_name"
    SET search_path TO :"db_name";

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA :"db_name";

DROP SCHEMA IF EXISTS public CASCADE;
