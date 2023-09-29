# Devicehub

Devicehub is a distributed IT Asset Management System focused on reusing digital devices, created under the [eReuse.org](https://www.ereuse.org) initiative.

This README explains how to install and use Devicehub. [The documentation](http://devicehub.ereuse.org) explains the concepts, usage and the API.

Devicehub is built with [Teal](https://github.com/ereuse/teal) and [Flask](http://flask.pocoo.org). 

Devicehub relies on the existence of an [API_DLT connector](https://gitlab.com/dsg-upc/ereuse-dpp) verifiable data registry service, where certain operations are recorded to keep an external track record (ledger).

# Installing
Please visit the [Manual Installation](README_MANUAL_INSTALLATION.md) instructions to understand the detailed steps to install it locally or deploy it on a server.

# Docker
There is a Docker compose file for an automated deployment. The next steps describe how to run and use it.

1. Download the sources:
```
  git clone https://github.com/eReuse/devicehub-teal.git -b dpp
  cd devicehub-teal
```

2. If you want to initialize your DeviceHub instance with a sample device snapshot you can copy it into that directory. 
```
  cp snapshot01.json examples/snapshots/
```

 Otherwise, the device inventory of your DeviceHub instance will be empty and ready to add new devices. For that you need to change the var to 'n' in the **.env** file
```
  IMPORT_SNAPSHOTS='n'
```

To register new devices, the [workbench software](https://github.com/eReuse/workbench) can be run on a device to generate a hardware snapshot that can be uploaded to your DeviceHub instance.

3. Modify the environment variables in the file .env You can find one example in examples/env.example.
If you don't have any, you can copy that example and modify the basic vars
```
  cp examples/env.example .env
```
You can use these parameters as default for a local test, but default values may not be suitable for an internet-exposed service for security reasons. However, these three variables need to be initialized:
```
  API_DLT
  API_DLT_TOKEN
  API_RESOLVER
```
These values should come from an already operational [API_DLT connector](https://gitlab.com/dsg-upc/ereuse-dpp) service instance.

4. Run the docker containers:
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
  devicehub-teal-devicehub-id-client-1  |  * Running on http://172.28.0.2:5000/ (Press CTRL+C to quit)
  devicehub-teal-devicehub-id-server-1  |  * Running on all addresses.
  devicehub-teal-devicehub-id-server-1  |    WARNING: This is a development server. Do not use it in a production deployment.
  devicehub-teal-devicehub-id-server-1  |  * Running on http://172.28.0.5:5000/ (Press CTRL+C to quit)
```

That means the two Devicehub instances are running in their containers, that can be reached as http://localhost:5000/ and http://localhost:5001/

5. To shut down the services and remove the corresponding data, you can use:
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

6. These are the details for use in this implementation:

  Devicehub with url (http://localhost:5000) is the identity provider of OIDC and have user defined in **.env** file with SERVER_ID_EMAIL_DEMO var.

  Devicehub with url (http://localhost:5001) is the client identity of OIDC and have user defined in **.env** file with SERVER_ID_EMAIL_DEMO var.

  You can change these values in the *.env* file

7. If you want to use Workbench for these DeviceHub instances you need to go to
```
  http://localhost:5001/workbench/
```
with the demo user and then download the settings and ISO files. Follow the instructions that appear on the [help](https://help.usody.com/en/setup/setup-pendrive/) page.
