"""
Fabfile to perform automatic deployment

Usage examples:
List all available commands:
$ fab -l

Print command specific help:
$ fab bootstrap -h

Execute 'bootstrap' task on 'devel.ereuse.org' host:
$ fab -H devel.ereuse.org bootstrap
"""

import os
import sys
from fabric import task


PACKAGES_BASE = ['git', 'python3', 'python3-virtualenv', 'postgresql', 'postgresql-client']

PACKAGES_WEASYPRINT = ['build-essential', 'python3-dev', 'python3-pip', 'python3-setuptools', 'python3-wheel', 'python3-cffi',
                       'libcairo2', 'libpango-1.0-0', 'libpangocairo-1.0-0', 'libgdk-pixbuf2.0-0', 'libffi-dev', 'shared-mime-info']

PACKAGES = PACKAGES_BASE + PACKAGES_WEASYPRINT

GIT_REPO_URL = 'https://github.com/eReuse/devicehub-teal.git'


@task(
    help={
        'domain': 'domain where app will be deployed',
        'branch': 'select branch to clone from git',
    }
)
def bootstrap(c, domain='api.ereuse.org', branch='testing'):
    """
    Prepare a machine to host a devihub instance

    Usually it's only required to run once by host.
    """
    install_apt_dependencies(c)

    deployment = AppDeployment(domain, c)

    deployment.clone_devicehub_repository()
    deployment.install_package_requirements()

    # TODO(@slamora)
    deployment.initialize_database()

    deployment.setup_wsgi_app()
    # deployment.configure_apache2()


def install_apt_dependencies(c):
    c.sudo('apt-get update -qy')
    c.sudo('apt-get install -qy {}'.format(' '.join(PACKAGES)))
    c.sudo('sudo -u postgres psql postgres -c "SELECT version()" | grep PostgreSQL')


class AppDeployment:
    """
    app dir schema:
    ~/sites/domain/
        devicehub   # source code
        source      # wsgi app
        venv        # python virtual environment
    """
    SITES_PATH = '~/sites/'
    GIT_CLONE_DIR = 'devicehub'
    VENV_DIR = 'venv'

    def __init__(self, domain, connection):
        self.c = connection
        self.base_path = os.path.join(self.SITES_PATH, domain)
        self.git_clone_path = os.path.join(self.base_path, self.GIT_CLONE_DIR)
        self.venv_path = os.path.join(self.base_path, self.VENV_DIR)

    def clone_devicehub_repository(self):
        params = {
            'branch': 'testing',
            'repo': GIT_REPO_URL,
            'path': self.git_clone_path,
        }
        self.c.run('rm -rf {}'.format(params['path']))
        # TODO use optimized clone (only target branch)
        # self.c.run('git clone -b {branch} --single-branch {repo} {path}'.format(**params))
        self.c.run('git clone -b {branch} {repo} {path}'.format(**params))

    def install_package_requirements(self):
        self.c.run('python3 -m virtualenv -p python3.7 {}'.format(self.venv_path))
        self.c.run('{}/bin/pip install -r {}/requirements.txt'.format(self.venv_path, self.git_clone_path))

    def initialize_database(self):
        self.c.run('{}/bin/pip install -e {}'.format(self.venv_path, self.git_clone_path))
        self.c.run('{}/bin/pip install alembic'.format(self.venv_path))

        # TODO run the following commands when PR #30 is merged
        """
        # Playground with alembic migrations
        sudo su - postgres
        bash examples/create-db.sh devicehub dhub
        exit
        git checkout feature/alembic-migrations
        export dhi=dbtest; dh inv add --common --name dbtest

        """

    def setup_wsgi_app(self):
        self.c.sudo('apt-get install -qy libapache2-mod-wsgi-py3')

        wsgi_file = os.path.join(self.git_clone_path, 'examples/wsgi.py')
        wsgi_path = os.path.join(self.base_path, 'source')
        self.c.run('mkdir -p {}'.format(wsgi_path))
        self.c.run('cp {file} {path}'.format(file=wsgi_file, path=wsgi_path))

    def configure_apache2(self):
        """Configure apache2 + wsgi & restart service"""
        # 1. read examples/apache.conf and set domain
        # TODO update apache config with
        # https://flask.palletsprojects.com/en/1.1.x/deploying/mod_wsgi/#support-for-automatic-reloading

        # 2. cp examples/apache.conf /etc/apache2/sites-available/{domain}.conf

        # 3. enable site
        # a2ensite api.app.usody.com.conf

        # check if everything is OK (e.g. apache running? wget {domain})
        result = self.c.run('apachectl configtest')
        if result.failed:
            sys.exit('Error while autoconfiguring apache.\n' + result.stderr)

        # 4. Restart apache

        # XXX. touch the .wsgi file to trigger a reload in mod_wsgi (REQUIRED ON UPDATING NOT ON BOOSTRAP)
