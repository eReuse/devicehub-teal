project := dkr-dsg.ac.upc.edu/ereuse

branch := `git branch --show-current`
commit := `git log -1 --format=%h`
tag := ${branch}__${commit}

# docker images
devicehub_image := ${project}/devicehub:${tag}
postgres_image := ${project}/postgres:${tag}

# 2. Create a virtual environment.
docker_build:
	docker build -f docker/devicehub.Dockerfile -t ${devicehub_image} .
	# DEBUG
	#docker build -f docker/devicehub.Dockerfile -t ${devicehub_image} . --progress=plain --no-cache

	docker build -f docker/postgres.Dockerfile -t ${postgres_image} .
	# DEBUG
	#docker build -f docker/postgres.Dockerfile -t ${postgres_image} . --progress=plain --no-cache
	@printf "\n##########################\n"
	@printf "\ndevicehub image: ${devicehub_image}\n"
	@printf "postgres image: ${postgres_image}\n"
	@printf "\ndocker images built\n"
	@printf "\n##########################\n\n"

docker_publish:
	docker push ${devicehub_image}
	docker push ${postgres_image}

.PHONY: docker
docker:
	$(MAKE) docker_build
	$(MAKE) docker_publish
	@printf "\ndocker images published\n"

# manage 2 kinds of deployments with docker compose

dc_up_devicehub:
	docker compose -f docker-compose_devicehub.yml up || true

dc_down_devicehub:
	docker compose -f docker-compose_devicehub.yml down -v || true

dc_up_devicehub_dpp:
	docker compose -f docker-compose_devicehub-dpp.yml up || true

dc_down_devicehub_dpp:
	docker compose -f docker-compose_devicehub-dpp.yml down -v || true
