project := dkr-dsg.ac.upc.edu/devicehub

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

docker_publish:
	docker push ${devicehub_image}
	docker push ${postgres_image}

.PHONY: docker
docker:
	$(MAKE) docker_build
	$(MAKE) docker_publish
	@printf "\nimage: ${devicehub_image}\n"
	@printf "\nimage: ${postgres_image}\n"
	@printf "\ndocker images built and published\n"
