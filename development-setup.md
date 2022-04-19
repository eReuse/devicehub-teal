# Setup developement project

## Installing

complete this steps from [README - Installing](README.md#installing)

## Setup project

Create a PostgreSQL database called devicehub by running [create-db](examples/create-db.sh):

- Start postgresDB
- `bash examples/create-db.sh devicehub dhub, and password ereuse.`
- `cp examples/env.example .env`

Create a secretkey and add into `.env`

```bash
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex())')" >> .env
```

Using the dh tool for set up with one or multiple inventories. Create the tables in the database by executing:

```bash
export dhi=dbtest; dh inv add --common --name dbtest
```

Create a demo table

```bash
export dhi=dbtest; dh dummy
```

## Run project

Run the app

```bash
export FLASK_APP=app.py; export FLASK_ENV=development; flask run --debugger
```

Finally login into `localhost:5000/login/`

- User: user@dhub.com
- Pass: 1234

## Troubleshooting

- If when execute dh command it thows an error, install this dependencies in your distro
  - `sudo apt install -y libpango1.0-0 libcairo2 libpq-dev`
