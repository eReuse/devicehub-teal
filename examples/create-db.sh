#!/usr/bin/env bash
# Creates a database, user, and extensions to use Devicehub

createdb $1  # Create main database
psql -d $1 -c "CREATE USER dhub WITH PASSWORD 'ereuse';" # Create user Devicehub uses to access db
psql -d $1 -c "GRANT ALL PRIVILEGES ON DATABASE $1 TO dhub;" # Give access to the db
psql -d $1 -c "CREATE EXTENSION pgcrypto SCHEMA public;" # Enable pgcrypto
psql -d $1 -c "CREATE EXTENSION ltree SCHEMA public;" # Enable ltree
psql -d $1 -c "CREATE EXTENSION citext SCHEMA public;" # Enable citext
