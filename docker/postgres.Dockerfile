FROM postgres:15.4-bookworm
# this is the latest in 2023-09-14_13-01-38
#FROM postgres:latest

# Add a SQL script that will be executed upon container startup
COPY docker/postgres.setupdb.sql /docker-entrypoint-initdb.d/

EXPOSE 5432
