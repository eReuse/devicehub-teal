#!/usr/bin/env bash
# Creates a database, user, and extensions to use Devicehub
# $1 is the database to create
# $2 is the user to create and give full permissions on the database
# This script asks for the password of such user

db=$1
user=$2
pass=$3

grant="GRANT ALL PRIVILEGES ON DATABASE $db TO $user;" # Give access to the db
pgcrypto='CREATE EXTENSION pgcrypto SCHEMA public;' # Enable pgcrypto
ltree='CREATE EXTENSION ltree SCHEMA public;' # Enable ltree
citext='CREATE EXTENSION citext SCHEMA public;' # Enable citext
pg_trgm='CREATE EXTENSION pg_trgm SCHEMA public;' # Enable pg_trgm

su - postgres -c "createdb $db" # Create main database
su - postgres -c "psql -a -c \"CREATE USER $user WITH PASSWORD '$pass';\"" # Create user Devicehub uses to access db
su - postgres -c "psql -a -c \"$grant\""
su - postgres -c "psql -d $db -c \"$pgcrypto\""
su - postgres -c "psql -d $db -c \"$ltree\""
su - postgres -c "psql -d $db -c \"$citext\""
su - postgres -c "psql -d $db -c \"$pg_trgm\""
