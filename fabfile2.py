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
from fabric import task, Connection


PACKAGES_BASE = ['git', 'python3', 'python3-virtualenv', 'postgresql', 'postgresql-client']

PACKAGES_WEASYPRINT = ['build-essential', 'python3-dev', 'python3-pip', 'python3-setuptools',
                       'python3-wheel', 'python3-cffi', 'libcairo2', 'libpango-1.0-0',
                       'libpangocairo-1.0-0', 'libgdk-pixbuf2.0-0', 'libffi-dev',
                       'shared-mime-info']

PACKAGES = PACKAGES_BASE + PACKAGES_WEASYPRINT

GIT_REPO_URL = 'https://github.com/eReuse/devicehub-teal.git'


TASK_COMMON_HELP = {
        'domain': 'domain where app will be deployed',
        'branch': 'select branch to clone from git',
    }

@task(
    help=TASK_COMMON_HELP,
)

def bootstrap(c, domain='api.ereuse.org', branch='master'):
    """
    Prepare a machine to host a devihub instance

    Usually it's only required to run once by host.
    """
    install_apt_dependencies(c)

    deployment = AppDeployment(domain, branch, c)

    deployment.clone_devicehub_repository()
    deployment.install_package_requirements()

    # TODO(@slamora)
    deployment.initialize_database()

    deployment.setup_wsgi_app()
    # deployment.setup_apache2()
    deployment.setup_nginx()
    deployment.setup_gunicorn()


@task(
    help=TASK_COMMON_HELP,
)
def upgrade(c, domain='api.ereuse.org', branch='master'):
    """
    Upgrade a running instance of devicehub to the latest version of
    the specified git branch.
    """
    deployment = AppDeployment(domain, branch, c)
    deployment.upgrade_devicehub_code()
    deployment.upgrade_package_requirements()
    deployment.upgrade_database_schema()
    deployment.restart_services()





class AppDeployment:
    """
    app dir schema:
    ~/sites/<domain>/
        devicehub   # source code
        source      # wsgi app
        venv        # python virtual environment
    """
    SITES_PATH = '/home/ereuse/sites/'
    GIT_CLONE_DIR = 'devicehub'
    VENV_DIR = 'venv'

    def __init__(self, domain, branch, host='localhost', port=10022):
        self.host = host
        self.port = port
        self.branch = branch
        self.c = self.connection()
        self.base_path = os.path.join(self.SITES_PATH, domain)
        self.git_clone_path = os.path.join(self.base_path, self.GIT_CLONE_DIR)
        self.venv_path = os.path.join(self.base_path, self.VENV_DIR)
        self.setup_tag_provider()
        self.cmd = 'su - ereuse -c \'{}\''.format
        self.db_user = 'dhub'
        self.db_pass = 'ereuse'
        self.db = 'devicehub'

    def connection(self):
        connect = Connection(self.host)
        connect.user = 'root'
        connect.port = self.port
        return connect

    def install_apt_dependencies(self):
        self.c.run('apt-get update -qy')
        self.c.run('apt-get install -qy {}'.format(' '.join(PACKAGES)))
        self.c.run('su - postgres -c \'psql postgres -c "SELECT version()" | grep PostgreSQL\'')

    def bootstrap(self):
        self.install_apt_dependencies()
        self.clone_devicehub_repository()
        self.install_package_requirements()
        self.initialize_database()

    def clone_devicehub_repository(self):
        params = {
            'branch': self.branch,
            'repo': GIT_REPO_URL,
            'path': self.git_clone_path,
        }

        self.c.run(self.cmd('rm -rf {}'.format(params['path'])))
        # TODO use optimized clone (only target branch)
        # self.c.run('git clone -b {branch} --single-branch {repo} {path}'.format(**params))
        self.c.run(self.cmd('git clone -b {branch} {repo} {path}'.format(**params)))

    def install_package_requirements(self):
        self.c.run(self.cmd('python3 -m virtualenv -p python3.7 {}'.format(self.venv_path)))
        self.upgrade_package_requirements()

    def upgrade_package_requirements(self):
        command = self.cmd('{}/bin/pip install -r {}/requirements.txt'.format(
            self.venv_path, self.git_clone_path))
        self.c.run(command)
        self.c.run(self.cmd('{}/bin/pip install gunicorn==20.0.4'.format(self.venv_path)))

    def initialize_database(self):
        db = self.db
        user = self.db_user
        password = self.db_pass

        command = '{}/bin/pip install -e {}'.format(self.venv_path, self.git_clone_path)
        self.c.run(self.cmd(command))

        self.c.run(self.cmd('{}/bin/pip install alembic'.format(self.venv_path)))

        command = 'sh {}/examples/init_db.sh {} {} {}'.format(self.git_clone_path, db, user,
            password)
        self.c.run(command)

    def dh_inv_add(self):
        # import pdb; pdb.set_trace()
        command = 'export dhi=dbtest; {}/bin/dh inv add --common --name dbtest'.format(
            self.venv_path)
        self.c.run(self.cmd(command))

        # TODO run the following commands when PR #30 is merged
        """
        # Playground with alembic migrations
        sudo su - postgres
        bash examples/create-db.sh devicehub dhub
        exit
        git checkout feature/alembic-migrations
        export dhi=dbtest; dh inv add --common --name dbtest

        """

    def setup_tag_provider(self):
        """
        We need define the correct tag_provider in common.inventory
        """
        text_info = """
        devicehub_testing=# SELECT * FROM common.inventory;

                    updated            |            created            |    id     |   name   |    tag_provider    |              tag_token               |                org_id
        -------------------------------+-------------------------------+-----------+----------+--------------------+--------------------------------------+--------------------------------------
        2020-07-16 16:53:57.722325+02 | 2020-07-16 16:53:57.725848+02 | usodybeta | Test 1   | http://example.com | 9f564863-2d28-4b69-a541-a08c5b34d422 | df7496df-d3e4-4286-a76a-350464e00181
        """
        print("It is necessary modify manualy tha tag_provider")
        print(text_info)

    def upgrade_devicehub_code(self):
        params = {
            'path': self.git_clone_path,
        }
        result = self.c.run(self.cmd('cd {path} && git pull --ff-only'.format(**params)))
        if result.failed:
            raise RuntimeError("Error retrieving latest devicehub code: {}".format(result.stderr))

    def upgrade_database_schema(self):
        # TODO run the following commands when PR #30 is merged
        """
        alembic -x inventory=dbtest upgrade head
        """

    def setup_wsgi_app(self):
        self.c.sudo('apt-get install -qy libapache2-mod-wsgi-py3')

        wsgi_file = os.path.join(self.git_clone_path, 'examples/wsgi.py')
        wsgi_path = os.path.join(self.base_path, 'source')
        self.c.run('mkdir -p {}'.format(wsgi_path))
        self.c.run('cp {file} {path}'.format(file=wsgi_file, path=wsgi_path))

    def setup_nginx(self):
        """Configure ngnix & restart service"""
        # 0. install nginx
        file_conf = os.path.join(self.git_clone_path, 'examples/01_api.dh.usody.net.conf')
        file_conf_nginx = os.path.split(file_conf)[-1]
        self.c.sudo('apt-get install -qy nginx')
        self.c.sudo('cp {} /etc/nginx/sites-available/'.format(file_conf))
        self.c.sudo('ln -sf /etc/nginx/sites-available/{} /etc/nginx/sites-enabled/'.format(file_conf_nginx))
        result = self.c.sudo('nginx -t')
        if result.failed:
            sys.exit('Error while autoconfiguring nginx.\n' + result.stderr)
        #self.c.sudo('systemctl restart nginx')

    def setup_gunicorn(self):
        """Configure gunicorn & restart service"""
        # 0. install nginx
        file_conf = os.path.join(self.git_clone_path, 'examples/gunicorn.service')
        self.c.sudo('cp {} /etc/systemd/system/'.format(file_conf))
        self.c.sudo('mkdir -p /var/log/gunicorn')
        self.c.sudo('chown ereuse.ereuse /var/log/gunicorn')
        #self.c.sudo('systemctl daemon-reload')
        #self.c.sudo('systemctl restart gunicorn.service')

    def setup_apache2(self):
        """Configure apache2 + wsgi & restart service"""
        # 0. install apache2
        self.c.sudo('apt-get install -qy apache2')

        # 1. read examples/apache.conf and set domain
        # TODO update apache config with
        # https://flask.palletsprojects.com/en/1.1.x/deploying/mod_wsgi/#support-for-automatic-reloading

        # 2. cp examples/apache.conf /etc/apache2/sites-available/{domain}.conf

        # 3. enable site
        # a2ensite api.app.usody.com.conf

        # check if everything is OK (e.g. apache running? wget {domain})
        result = self.c.sudo('apachectl configtest')
        if result.failed:
            sys.exit('Error while autoconfiguring apache.\n' + result.stderr)

        # 4. Restart apache
        # self.c.sudo("systemctl restart apache2")

    def restart_services(self):
        # XXX. touch the .wsgi file to trigger a reload in mod_wsgi (REQUIRED ON UPDATING NOT ON BOOSTRAP)
        self.c.sudo("systemctl reload apache2")


app = AppDeployment('api.usody.net', 'feature/fabfile-continuous-deployment')
