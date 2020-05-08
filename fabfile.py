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
GIT_CLONE_PATH = 'devicehub'
VENV_PATH = os.path.join(GIT_CLONE_PATH, 'env')


@task(help={'branch': 'select branch to clone from git'})
def bootstrap(c, branch='testing'):
    """
    Prepare a machine to host a devihub instance

    Usually it's only required to run once by host.
    """
    install_apt_dependencies(c)
    clone_devicehub_repository(c)
    install_package_requirements(c)

    # TODO(@slamora)
    # configure flask app
    # initialize database
    # configure apache2 + wsgi & restart service


def install_apt_dependencies(c):
    c.sudo('apt-get update -qy')
    c.sudo('apt-get install -qy {}'.format(' '.join(PACKAGES)))
    c.sudo('sudo -u postgres psql postgres -c "SELECT version()" | grep PostgreSQL')


def install_package_requirements(c):
    c.run('virtualenv -p python3 {}'.format(VENV_PATH))
    c.run('{}/bin/pip install -r {}/requirements.txt'.format(VENV_PATH, GIT_CLONE_PATH))


def clone_devicehub_repository(c):
    params = {
        'branch': 'testing',
        'repo': GIT_REPO_URL,
        'path': GIT_CLONE_PATH,
    }
    c.run('rm -rf {}'.format(GIT_CLONE_PATH))
    c.run('git clone -b {branch} --single-branch {repo} {path}'.format(**params))
