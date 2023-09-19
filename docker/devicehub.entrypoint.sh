#!/bin/sh

set -e
set -u
# DEBUG
set -x

# 3. Generate an environment .env file.
gen_env_vars() {
        # generate config using env vars from docker
        cat > .env <<END
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=${DB_HOST}
DB_DATABASE=${DB_DATABASE}
SCHEMA=dbtest
DB_SCHEMA=dbtest
HOST=${HOST}
EMAIL_DEMO=${EMAIL_DEMO}
PASSWORD_DEMO=${PASSWORD_DEMO}
JWT_PASS=${JWT_PASS}
SECRET_KEY=${SECRET_KEY}

API_DLT=${API_DLT}
API_RESOLVER=${API_RESOLVER}
API_DLT_TOKEN=${API_DLT_TOKEN}
ID_FEDERATED=${ID_FEDERATED}

OAUTH2_JWT_ENABLED=True
OAUTH2_JWT_ISS=https://authlib.org
OAUTH2_JWT_KEY=secret-key
OAUTH2_JWT_ALG=HS256

URL_MANUALS=${URL_MANUALS}
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
        # 8. Running alembic from oidc module.y
        cd ereuse_devicehub/modules/oidc
        alembic -x inventory=dbtest upgrade head
        cd -
        # 9. Running alembic from dpp module.
        cd ereuse_devicehub/modules/dpp/
        alembic -x inventory=dbtest upgrade head
        cd -

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

handle_federated_id() {

        # devicehub host and id federated checker

        EXPECTED_ID_FEDERATED="$(curl -s "${API_RESOLVER}/getAll" \
                | jq -r '.url | to_entries | .[] | select(.value == "'"${DEVICEHUB_HOST}"'") | .key' \
                | head -n 1)"

        # if is a new DEVICEHUB_HOST, then register it
        if [ -z "${EXPECTED_ID_FEDERATED}" ]; then
                # TODO better docker compose run command
                cmd="docker compose run --entrypoint= devicehub flask dlt_insert_members ${DEVICEHUB_HOST}"
                big_error "No FEDERATED ID maybe you should run \`${cmd}\`"
        fi

        # if not new DEVICEHUB_HOST, then check consistency

        # if there is already an ID in the DLT, it should match with my internal ID
        if [ ! "${EXPECTED_ID_FEDERATED}" = "${ID_FEDERATED}" ]; then

                big_error "ID_FEDERATED should be ${EXPECTED_ID_FEDERATED} instead of ${ID_FEDERATED}"
        fi

        # not needed, but reserved
        # EXPECTED_DEVICEHUB_HOST="$(curl -s "${API_RESOLVER}/getAll" \
        #         | jq -r '.url | to_entries | .[] | select(.key == "'"${ID_FEDERATED}"'") | .value' \
        #         | head -n 1)"
        # if [ ! "${EXPECTED_DEVICEHUB_HOST}" = "${DEVICEHUB_HOST}" ]; then
        #         big_error "ERROR: DEVICEHUB_HOST should be ${EXPECTED_DEVICEHUB_HOST} instead of ${DEVICEHUB_HOST}"
        # fi

}

main() {

        gen_env_vars

        wait_for_postgres

        init_flagfile='/container_initialized'
        if [ ! -f "${init_flagfile}" ]; then

                # 7, 8, 9, 11
                init_data

                # 12. Add a new server to the 'api resolver'
                handle_federated_id

                # 13. Do a rsync api resolve
                flask dlt_rsync_members

                # 14. Register a new user to the DLT
                flask dlt_register_user "${EMAIL_DEMO}" ${PASSWORD_DEMO} Operator

                # non DL user (only for the inventory)
                #   flask adduser user2@dhub.com ${PASSWORD_DEMO}

                # # 15. Add inventory snapshots for user "${EMAIL_DEMO}".
                cp /mnt/snapshots/snapshot*.json ereuse_devicehub/commands/snapshot_files
                /usr/bin/time flask snapshot "${EMAIL_DEMO}" ${PASSWORD_DEMO}

                # # 16.
                flask check_install "${EMAIL_DEMO}" ${PASSWORD_DEMO}

                # remain next command as the last operation for this if conditional
                touch "${init_flagfile}"
        fi

        # 17. Use gunicorn
        #   thanks https://akira3030.github.io/formacion/articulos/python-flask-gunicorn-docker.html
        # TODO meanwhile no nginx (step 19), gunicorn cannot serve static files, then we prefer development server
        #gunicorn --access-logfile - --error-logfile - --workers 4 -b :5000 app:app
        #   alternative: run development server
        flask run --host=0.0.0.0 --port 5000

        # DEBUG
        #sleep infinity
}

main "${@}"
