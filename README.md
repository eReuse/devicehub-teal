# Devicehub

Devicehub is a distributed IT Asset Management System focused on reusing digital devices, created under the project [eReuse.org](https://www.ereuse.org)

This README explains how to install and use Devicehub. [The documentation](http://devicehub.ereuse.org) explains the concepts and the API.

Devicehub is built with [Teal](https://github.com/ereuse/teal) and [Flask](http://flask.pocoo.org).

# Installing
Please visit the [Manual Installation](README_MANUAL_INSTALLATION.md) to understand the detailed steps to install it locally or deploy it on a server.

# Docker
There is a Docker compose file for an automated deployment. In the next steps, we can see how to run and use it.

1. Download the sources:
```
  git clone https://github.com/eReuse/devicehub-teal.git
  cd devicehub-teal
```

2. You need to decide on one directory in your system for sharing documents between your system and the dockers.
As an example we use "/tmp/dhub/" and need to create it:
```
  mkdir /tmp/dhub
```

3. If you want to initialize your DeviceHub instance with sample device snapshop you can copy your snapshots, copy your snapshots in this directory. If you don't have any snapshots copy one of the example directory. Otherwise, the device inventory of your DeviceHub instance will be empty and ready to add new devices. To register new devices, the [workbench software](https://github.com/eReuse/workbench) can be run on a device to generate a hardware snapshot that can be uploaded to your DeviceHub instance.

3. Copy your snapshots in this directory. If you don't have any snapshots copy one of the example directory.
```
  cp examples/snapshot01.json /tmp/dhub
```

4. Modify the file with environment variables in the file .env You can see one example in examples/env
If you don't have one, please copy the examples/env file and modify the basic vars
```
  cp examples/env.example .env
```
You can use these parameters for default as a test, but you need to add values in these three variables:
```
  API_DLT
  API_DLT_TOKEN
  API_RESOLVER
```

5. run the dockers:
```
  docker compose up
```
To stop the dockers you can use Ctl+C, and if you run again "compose up" you'll maintain the data and infrastructure.

In the screen you can see all the process of install. If there are any problem you can see this errors in the screen.

If the last line you see one text like this, *exited whit code*:
```
  devicehub-teal-devicehub-id-client-1 exited with code 1
```
Then the install went wrong.

6. If you want to down the volumes and remove the data, you can use:
```
  docker compose down -v
```

7. If you want to enter a shell inside a new container:
```
  docker run -it --entrypoint= ${target_docker_image} bash
```

If you want to enter a shell on an already running container:
```
  docker exec -it ${target_docker_image} bash
```

To know the valid value for ${target_docker_image} you can use:
```
  docker ps
```

8. These are the details for use in this implementation:

  *devicehub with port 5000* is the identity provider of OIDC and have user *user5000@example.com*

  *devicehub with port 5001* is the client identity of OIDC and have user *user5001@example.com*

  You can change these values in the *.env* file
