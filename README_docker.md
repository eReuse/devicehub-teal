# Devicehub

Devicehub is a distributed IT Asset Management System focused on reusing digital devices, created under the [eReuse.org](https://www.ereuse.org) initiative.

This README explains how to install and use Devicehub. [The documentation](http://devicehub.ereuse.org) explains the concepts, usage and the API.

Devicehub is built with [Teal](https://github.com/ereuse/teal) and [Flask](http://flask.pocoo.org). 

Devicehub relies on the existence of an [API_DLT connector](https://gitlab.com/dsg-upc/ereuse-dpp) verifiable data registry service, where certain operations are recorded to keep an external track record (ledger).

# Installing
Please visit the [Manual Installation](README.md) instructions to understand the detailed steps to install it locally or deploy it on a server.

# Docker
There is a Docker compose file for an automated deployment. The next steps describe how to run and use it.

1. Download the sources:
```
  git clone https://github.com/eReuse/devicehub-teal.git -b dpp
  cd devicehub-teal
```

2. Run the docker containers:
```
  docker compose up
```
To stop these docker containers you can use Ctl+C, and if you run again "compose up" you'll maintain the data and infrastructure state.

On the terminal screen, you can follow the installation steps. If there are any problems, error messages will appear here. The appearance of several warnings is normal and can be ignored.

If the last line you see one text like this, *exited whit code*:
```
  devicehub-teal-devicehub-id-client-1 exited with code 1
```
means the installation failed.

If the deployment was end-to-end successful (two running Devicehub instances successfully connected to the DLT backend selected in the .env file), you can see this text in the last lines:
```
  dhub-devicehub-1  |  * Running on all addresses.
  dhub-devicehub-1  |    WARNING: This is a development server. Do not use it in a production deployment.
  dhub-devicehub-1  |  * Running on http://172.19.0.4:5000/ (Press CTRL+C to quit)
  dhub-devicehub-1  |  * Restarting with stat
```

That means the two Devicehub instances are running in their containers, that can be reached as http://localhost:5000/ and http://localhost:5001/

3. To shut down the services and remove the corresponding data, you can use:
```
  docker compose down -v
```

If you want to enter a shell inside a **new instance of the container**:
```
  docker run -it --entrypoint= ${target_docker_image} bash
```

If you want to enter a shell on an **already running container**:
```
  docker exec -it ${target_docker_image} bash
```

To know the valid value for ${target_docker_image} you can use:
```
  docker ps
```

4. If you want to use Workbench for these DeviceHub instances you need to go to
```
  http://localhost:5001/workbench/
```
with the demo user and then download the settings and ISO files. Follow the instructions that appear on the [help](https://help.usody.com/en/setup/setup-pendrive/) page.
