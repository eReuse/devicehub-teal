# Devicehub

Devicehub is a distributed IT Asset Management System focused in reusing devices, created under the project [eReuse.org](https://www.ereuse.org)

This README explains how to install and use Devicehub. [The documentation](http://devicehub.ereuse.org) explains the concepts and the API.

Devicehub is built with [Teal](https://github.com/ereuse/teal) and [Flask](http://flask.pocoo.org).

# Installing
Please visit the [Manual Installation](#README_MANUAL_INSTALLATION.md) for understand how you can install locally or deploy in a server.

# Docker
You have a docker compose file for to do a automated deployment. In the next steps we can see as run and use.

1. Download the sources:
```
  git clone https://github.com/eReuse/devicehub-teal.git
  cd devicehub-teal
```

2. You need decide one dir in your system for share documents between your system and the dockers.
For us only as example we use "/tmp/dhub/" and need create it:
```
  mkdir /tmp/dhub
```

3. Copy your snapshots in this directory. If you don't have any snapshots copy one of the example directory.
```
  cp examples/snapshot01.json /tmp/dhub
```

4. Modify the file with environment variables in the file .env You can see one example in examples/env
If you don't have one please copy the examples/env file and modify the basic vars
```
  cp examples/env.example .env
```
You can use this parameters for default as a test, but you need add values in this three variables:
```
  API_DLT
  API_DLT_TOKEN
  API_RESOLVER
```

5. run the dockers:
```
  docker compose up
```
For stop the docker you can use Ctl+c and if you run again "compose up" you maintain the datas and infrastructure.

6. If you want down the volumens and remove the datas, you can use:
```
  docker compose down -v
```

7. If you want to enter a shell inside a new container:
```
  docker run -it --entrypoint= ${target_docker_image} bash
```

If you want to enter a shell on already running container:
```
  docker exec -it ${target_docker_image} bash
```

For to know the valid value for ${target_docker_image} you can use:
```
  docker ps
```

8. This are the details for use this implementation:

  *devicehub with port 5000* is the identity provider of oidc and have user *user5000@example.com*

  *devicehub with port 5001* is the client identity of oidc and have user *user5001@example.com*

  You can change this values in the file *.env*
