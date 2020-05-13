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
from fabric import task


PACKAGES = ['git', 'postgresql', 'postgresql-client']

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
    # install_apt_dependencies(c)

    deployment = AppDeployment(domain, c)
    deployment.clone_devicehub_repository()
    deployment.install_package_requirements()
    deployment.setup_wsgi_app()

    # TODO(@slamora)
    # initialize database
    # configure apache2 + wsgi & restart service


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
        self.c.run('git clone -b {branch} --single-branch {repo} {path}'.format(**params))

    def install_package_requirements(self):
        self.c.run('virtualenv -p python3 {}'.format(self.venv_path))
        self.c.run('{}/bin/pip install -r {}/requirements.txt'.format(self.venv_path, self.git_clone_path))

    def setup_wsgi_app(self):
        wsgi_file = os.path.join(self.git_clone_path, 'examples/wsgi.py')
        wsgi_path = os.path.join(self.base_path, 'source')
        self.c.run('mkdir -p {}'.format(wsgi_path))
        self.c.run('cp {file} {path}'.format(file=wsgi_file, path=wsgi_path))
