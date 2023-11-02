#!/bin/sh

set -e
set -u
# DEBUG
set -x

# 3. Generate an environment .env file.
gen_env_vars() {
        # generate config using env vars from docker
        cat > .env <<END
DB_USER='${DB_USER}'
DB_PASSWORD='${DB_PASSWORD}'
DB_HOST='${DB_HOST}'
DB_DATABASE='${DB_DATABASE}'
URL_MANUALS='${URL_MANUALS}'

HOST='${HOST}'

SCHEMA='dbtest'
DB_SCHEMA='dbtest'

JWT_PASS=${JWT_PASS}
SECRET_KEY=${SECRET_KEY}
END
}

wait_for_postgres() {
        # old one was
        #sleep 4

        default_postgres_port=5432
        # thanks https://testdriven.io/blog/dockerizing-django-with-postgres-gunicorn-and-nginx/
        while ! nc -z ${DB_HOST} ${default_postgres_port}; do
                sleep 0.5
        done
}

init_data() {

        # 7. Run alembic of the project.
        alembic -x inventory=dbtest upgrade head

        # 11. Generate a minimal data structure.
        #   TODO it has some errors (?)
        flask initdata || true
}

big_error() {
        local message="${@}"
        echo "###############################################" >&2
        echo "# ERROR: ${message}" >&2
        echo "###############################################" >&2
        exit 1
}

config_phase() {
        init_flagfile='docker__already_configured'
        if [ ! -f "${init_flagfile}" ]; then
                # 7, 11
                init_data

                if [ "${EMAIL_DEMO:-}" ] && [ "${PASSWORD_DEMO:-}" ]; then
                        flask adduser ${EMAIL_DEMO} ${PASSWORD_DEMO}
                fi

                # remain next command as the last operation for this if conditional
                touch "${init_flagfile}"
        fi
}

main() {

        gen_env_vars

        wait_for_postgres

        config_phase

        # 17. Use gunicorn
        #   thanks https://akira3030.github.io/formacion/articulos/python-flask-gunicorn-docker.html
        if [ "${DEPLOYMENT:-}" = "PROD" ]; then
                gunicorn --access-logfile - --error-logfile - --workers 4 -b :5000 app:app
        else
                # run development server
                FLASK_DEBUG=1 flask run --host=0.0.0.0 --port 5000
        fi
}

main "${@}"
