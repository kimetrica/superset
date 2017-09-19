#!/bin/sh
psql \
    --set=APP=$APP \
    --set=ENV=$ENV \
    --set=POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
    --username postgres -d postgres << EOF

\set ECHO all

\set REPORTER :APP '_reporter'
\set TEMPLATE 'template_' :APP

-- Create postgis_users role
CREATE ROLE postgis_users NOLOGIN NOCREATEDB NOCREATEROLE NOSUPERUSER;

-- Create application reporter role
CREATE ROLE :REPORTER NOLOGIN NOCREATEDB NOCREATEROLE NOSUPERUSER;

-- Create template database
CREATE DATABASE :TEMPLATE encoding 'utf8';

-- Configure the template database
\connect :TEMPLATE
CREATE EXTENSION postgis;
REVOKE ALL ON SCHEMA public FROM public;
GRANT USAGE ON SCHEMA public TO public;
GRANT USAGE ON SCHEMA public TO :REPORTER;
GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE public.geometry_columns TO postgis_users;
GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE public.spatial_ref_sys TO postgis_users;
GRANT SELECT ON public.geography_columns TO postgis_users;
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA PUBLIC FROM PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA PUBLIC TO postgis_users;

-- Superset
\set SCHEMA 'superset'
\set APP_USER :APP :ENV

-- Create application user
CREATE ROLE :APP_USER PASSWORD :'POSTGRES_PASSWORD' LOGIN CREATEDB NOCREATEROLE NOSUPERUSER;

-- In development and test environments, we can't set the database search path
-- on databases created by the test runner before migrations are run, and we can't
-- set it in the template database, so make sure the application user(s) is using
-- the correct search path
ALTER USER :APP_USER SET search_path=:SCHEMA,public,pg_temp;

-- Grant postgis_users to the application user
GRANT postgis_users to :APP_USER;

-- Make sure the application owner can create new schemas
GRANT CREATE ON DATABASE :TEMPLATE TO :APP_USER;

-- Create application schema
CREATE SCHEMA :SCHEMA;
ALTER SCHEMA :SCHEMA OWNER TO :APP_USER;
GRANT USAGE ON SCHEMA :SCHEMA TO :REPORTER;
ALTER DEFAULT PRIVILEGES IN SCHEMA :SCHEMA
  GRANT SELECT ON TABLES TO :REPORTER;

-- Finalize template database

\connect postgres

-- Mark the template database as a template
UPDATE pg_database SET datistemplate = true, datallowconn = false WHERE datname = :'TEMPLATE';

-- Create Application Database
CREATE DATABASE :APP:ENV template :TEMPLATE encoding 'utf8';

-- Configure the database search path
ALTER DATABASE :APP:ENV SET search_path=:SCHEMA,public,pg_temp;

-- Make sure the application owner can create new schemas
GRANT CREATE ON DATABASE :APP:ENV TO :APP_USER;

EOF
