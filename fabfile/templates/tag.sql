CREATE DATABASE {db};
CREATE USER {user} WITH PASSWORD '{db_pass}';
GRANT ALL PRIVILEGES ON DATABASE {db} TO {user};
