# Devicehub

Devicehub is a distributed IT Asset Management System focused in reusing devices, created under the project [eReuse.org](https://www.ereuse.org)

This README explains how to install and use Devicehub. [The documentation](http://devicehub.ereuse.org) explains the concepts and the API.

Devicehub is built with [Teal](https://github.com/ereuse/teal) and [Flask](http://flask.pocoo.org).

# Installing
The requirements are:

0. Required
-  python3.9
-  [PostgreSQL 11 or higher](https://www.postgresql.org/download/).
-  Weasyprint [dependencie](http://weasyprint.readthedocs.io/en/stable/install.html)

1. Generate a clone of the repository.
```
    git clone git@github.com:eReuse/devicehub-teal.git
    cd devicehub-teal
```

2. Create a virtual environment and install Devicehub with *pip*.
```
    python3.9 -m venv env
    source env/bin/activate
    pip3 install -U -r requirements.txt -e .
    pip3 install Authlib==1.2.1
```

3. Create a PostgreSQL database called *devicehub* by running [create-db](examples/create-db.sh):

-  In Linux, execute the following two commands (adapt them to your distro):

   1. `sudo su - postgres`.
   2. `bash examples/create-db.sh devicehub dhub`, and password `ereuse`.

-  In MacOS: `bash examples/create-db.sh devicehub dhub`, and password `ereuse`.

Configure project using environment file (you can use provided example as quickstart):
```bash
$ cp examples/env.example .env
```

4. Running alembic from oidc module.y
```
    alembic -x inventory=dbtest upgrade head
```

5. Running alembic from oidc module.y
```
    cd ereuse_devicehub/modules/oidc
    alembic -x inventory=dbtest upgrade head
```

6. Running alembic from dpp module.
```
    cd ereuse_devicehub/modules/dpp/
    alembic -x inventory=dbtest upgrade head
```

7. Add a suitable app.py file.
```
      cp examples/app.py .
```

8. Generate a minimal data structure.
```
      flask initdata
```
	
9. Add a new server to the 'api resolver' to be able to integrate it into the federation.
    The domain name for this new server has to be unique. When installing two instances their domain name must differ: e.g. dpp.mydomain1.cxm, dpp.mydomain2.cxm.
    If your domain is dpp.mydomain.cxm: 
```
    	flask dlt_insert_members http://dpp.mydomain.cxm
```

    modify the .env file as indicated in point 3.
    Add the corresponding 'DH' in ID_FEDERATED.
    example: ID_FEDERATED='DH10'

10. Do a rsync api resolve.
```
  	  flask dlt_rsync_members
```

11. Register a new user in devicehub.
```
  	  flask adduser email@cxm.cxm password
```

12. Register a new user to the DLT.
```
  	  flask dlt_register_user email@cxm.cxm password Operator
```

13. Finally, run the app:

```bash
$ flask run --debugger
```

The error ‘bdist_wheel’ can happen when you work with a *virtual environment*.
To fix it, install in the *virtual environment* wheel
package. `pip3 install wheel`

# Testing

1. `git clone` this project.
2. Create a database for testing executing `create-db.sh` like the normal installation but changing the first parameter from `devicehub` to `dh_test`: `create-db.sh dh_test dhub` and password `ereuse`.
3. Execute at the root folder of the project `python3 setup.py test`.

# Upgrade a deployment

For upgrade an instance of devicehub you need to do:

```bash
$ cd $PATH_TO_DEVIHUBTEAL
$ source venv/bin/activate
$ git pull
$ alembic -x inventory=dbtest upgrade head
```

If all migrations pass successfully, then it is necessary restart the devicehub.
Normaly you can use a little script for restart or run.
```
# systemctl stop gunicorn_devicehub.socket
# systemctl stop gunicorn_devicehub.service
# systemctl start gunicorn_devicehub.service
```

# OpenId Connect: 
We want to interconnect two devicehub instances already installed. One has a set of devices (OIDC client), the other has a set of users (OIDC identity server). Let's assume their domains are: dpp.mydomain1.cxm, dpp.mydomain2.cxm
20. In order to connect the two devicehub instances, it is necessary:
	* 20.1. Register a user in the devicehub instance acting as OIDC identity server.
	* 20.2. Fill in the openid connect form.
	* 20.3. Add in the OIDC client inventory the data of client_id, client_secret.
	
  For 20.1. This can be achieved on the terminal on the devicehub instance acting as OIDC identity server.
	```
  	  flask adduser email@cxm.cxm password
	```
	
	* 20.2. This is an example of how to fill in the form.

	In the web interface of the OIDC identity service, click on the profile of the just added user, select "My Profile" and click on "OpenID Connect":
	Then we can go to the "OpenID Connect" panel and fill out the form:

	The important thing about this form is:
	  * "Client URL" The URL of the OIDC Client instance, as registered in point 12. dpp.mydomain1.cxm in our example.
	  * "Allowed Scope" has to have these three words:
	  ```
	    openid profile rols
	  ```
    * "Redirect URIs" it has to be the URL that was put in "Client URL" plus "/allow_code"
	  * "Allowed Grant Types" has to be "authorization_code"
	  * "Allowed Response Types" has to be "code"
	  * "Token Endpoint Auth Method" has to be "Client Secret Basic"

	After clicking on "Submit" the "OpenID Connect" tab of the user profile should now include details for "client_id" and "client_secret".

	* 20.3. In the OIDC client inventory run: (in our example: url_domain is dpp.mydomain2.cxm, client_id and client_secret as resulting from the previous step)
	```
	  flask add_client_oidc url_domain client_id client_secret
	```
	After this step, both servers must be connected. Opening one DPP page on dpp.mydomain1.cxm (OIDC Client) the user can choose to authenticate using dpp.mydomain2.cxm (OIDC Server).

## Generating the docs


1. `git clone` this project.
2. Install plantuml. In Debian 9 is `# apt install plantuml`.
3. Execute `pip3 install -e .[docs]` in the project root folder.
4. Go to `<project root folder>/docs` and execute `make html`. Repeat this step to generate new docs.

To auto-generate the docs do `pip3 install -e .[docs-auto]`, then execute, in the root folder of the project `sphinx-autobuild docs docs/_build/html`.
