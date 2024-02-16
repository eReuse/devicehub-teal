#!/bin/sh

set -e
set -u
# DEBUG
set -x

main() {
        cd "$(dirname "${0}")"

        make docker_build
        docker compose up
}

main "${@}"
