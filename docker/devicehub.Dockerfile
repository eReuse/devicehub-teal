FROM debian:bullseye-slim

RUN apt update && apt-get install --no-install-recommends -y \
    python3-minimal \
    python3-pip \
    python-is-python3 \
    python3-psycopg2 \
    python3-dev \
    libpq-dev \
    build-essential \
    libpangocairo-1.0-0 \
    curl \
    jq \
    time \
    netcat

WORKDIR /opt/devicehub

# this is exactly the same as examples/pip_install.sh except the last command
#   to improve the docker layer builds, it has been separated
RUN pip install --upgrade pip
RUN pip install alembic==1.8.1    anytree==2.8.0    apispec==0.39.0    atomicwrites==1.4.0    blinker==1.5    boltons==23.0.0    cairocffi==1.4.0            cairosvg==2.5.2    certifi==2022.9.24    cffi==1.15.1            charset-normalizer==2.0.12    click==6.7    click-spinner==0.1.8    colorama==0.3.9    colour==0.1.5    cssselect2==0.7.0            defusedxml==0.7.1            et-xmlfile==1.1.0            flask==1.0.2                        flask-cors==3.0.10    flask-login==0.5.0    flask-sqlalchemy==2.5.1    flask-weasyprint==0.4    flask-wtf==1.0.0    hashids==1.2.0    html5lib==1.1    idna==3.4    inflection==0.5.1    itsdangerous==2.0.1            jinja2==3.0.3    mako==1.2.3    markupsafe==2.1.1                marshmallow==3.0.0b11                marshmallow-enum==1.4.1    more-itertools==8.12.0    numpy==1.22.0            odfpy==1.4.1    openpyxl==3.0.10    pandas==1.3.5    passlib==1.7.1    phonenumbers==8.9.11    pillow==9.2.0    pint==0.9    psycopg2-binary==2.8.3    py-dmidecode==0.1.0    pycparser==2.21    pyjwt==2.4.0    pyphen==0.13.0    python-dateutil==2.7.3            python-decouple==3.3    python-dotenv==0.14.0    python-editor==1.0.4    python-stdnum==1.9    pytz==2022.2.1    pyyaml==5.4            requests==2.27.1                requests-mock==1.5.2    requests-toolbelt==0.9.1    six==1.16.0                            sortedcontainers==2.1.0    sqlalchemy==1.3.24                    sqlalchemy-citext==1.3.post0    sqlalchemy-utils==0.33.11    tinycss2==1.1.1                tqdm==4.32.2    urllib3==1.26.12    weasyprint==44    webargs==5.5.3    webencodings==0.5.1                werkzeug==2.0.3            wtforms==3.0.1    xlrd==2.0.1   cryptography==39.0.1 Authlib==1.2.1 gunicorn==21.2.0

RUN pip install -i https://test.pypi.org/simple/ ereuseapitest==0.0.14

COPY . .
# this operation might be overriding inside container another app.py you would have
COPY examples/app.py .
RUN pip install -e .

COPY docker/devicehub.entrypoint.sh .
ENTRYPOINT sh ./devicehub.entrypoint.sh
