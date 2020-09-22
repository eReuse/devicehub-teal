#!/usr/bin/env bash
# Creates a database, user, and extensions to use Devicehub
# $1 is the database to create
# $2 is the user to create and give full permissions on the database
# This script asks for the password of such user

db=$1
user=$2
pass=$3

grant="GRANT ALL PRIVILEGES ON DATABASE $db TO $user;" # Give access to the db
pgcrypto='psql -d $db -c "CREATE EXTENSION pgcrypto SCHEMA public;"' # Enable pgcrypto
ltree='psql -d $db -c "CREATE EXTENSION ltree SCHEMA public;"' # Enable ltree
citext='psql -d $db -c "CREATE EXTENSION citext SCHEMA public;"' # Enable citext
pg_trgm='psql -d $db -c "CREATE EXTENSION pg_trgm SCHEMA public;"' # Enable pg_trgm

su - postgres -c "createdb $db" # Create main database
su - postgres -c "psql -c \"CREATE USER $user WITH PASSWORD '$pass';\"" # Create user Devicehub uses to access db

su - postgres -c 'psql -c "$grant"'
su - postgres -c '$pgcrypto'
su - postgres -c '$ltree'
su - postgres -c '$citext'
su - postgres -c '$pg_trgm'
