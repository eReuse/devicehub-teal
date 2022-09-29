# Contributing to devicehub

## Writing code

### Javascript and compatibility with "old" browsers
**Warning:** This project is using babel compiler... You need run an additional build step to make build js file
```bash
npm install
npm run babel
```
NOTE: If you prefer you can use yarn instead, it's compatible
NOTE2: This only affect to file `ereuse_devicehub/static/js/main_inventory.js`.

### Coding style

#### Python style
- Unless otherwise specified, follow [PEP 8](https://www.python.org/dev/peps/pep-0008). Use [flake8](https://pypi.org/project/flake8/) to check for problems in this area.
- Use [isort](https://github.com/PyCQA/isort#readme) to automate import sorting.

To automatize this work just configure `pre-commit` hooks in your development environment:
```bash
# on your virtual environment
pip install -r requirements-dev.txt
pre-commit install
```

#### HTML (templates)
- Template file names should be all lowercase, using underscores instead of camelCase.

  Do this: `device_detail.html`

  Don't do this: `DeviceDetail.html`, `Device-detail.html`


## Adding a new dependency to the project
This project tracks its packages using pip-tools, it could be installed by running:
```
pip install pip-tools
```

Whenever you need to install a new package using pip install <package-name>:
1. Put the package name into `requirements.in` instead.
```
# requirements.in
...
new_package
```

2. Compile the requirements
```
pip-compile requirements.in --output-file=requirements.txt

```

3. Then install upgraded dependencies:
```
pip install -U -r requirements.txt
```
