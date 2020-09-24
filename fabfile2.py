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
        self.user = 'ereuse'
        self.db_user = 'dhub'
        self.db_pass = 'ereuse'
        self.db = 'devicehub'
        self.db_host = 'localhost'
        self.domain = domain
        self.name_service = domain.replace('.', '_')
        self.def_cmds()

    def def_cmds(self):
        # General command for ereuse
        base = 'su - {} '.format(self.user)
        self.cmd = (base + '-c \'{}\'').format

        # Command for ereuse into of enviroment
        path_env = (base + ' -c \'cd {}; source ../venv/bin/activate;').format(self.git_clone_path)
        path_env += '{}\''
        self.cmd_env = path_env.format

    def connection(self):
        connect = Connection(self.host)
        connect.user = 'root'
        connect.port = self.port
        return connect

    def bootstrap(self):
        self.install_apt_dependencies()
        self.clone_devicehub_repository()
        self.install_package_requirements()
        self.initialize_database()

    def install_apt_dependencies(self):
        self.c.run('apt-get update -qy')
        self.c.run('apt-get install -qy {}'.format(' '.join(PACKAGES)))
        self.c.run('su - postgres -c \'psql postgres -c "SELECT version()" | grep PostgreSQL\'')

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

        command = 'pip install -e {}'.format(self.git_clone_path)
        self.c.run(self.cmd_env(command))
        self.c.run(self.cmd_env('pip install alembic'))

    def upgrade_package_requirements(self):
        command = self.cmd_env('pip install -r {}/requirements.txt'.format(self.git_clone_path))
        self.c.run(command)
        self.c.run(self.cmd_env('pip install gunicorn==20.0.4'))

    def initialize_database(self):
        # create database, user and extensions
        command = 'sh {}/examples/init_db.sh {} {} {}'.format(self.git_clone_path, self.db,
            self.db_user, self.db_pass)
        self.c.run(command)

        # create schemes in database
        command = 'export dhi=dbtest; dh inv add --common --name dbtest'
        self.c.run(self.cmd_env(command))
        self.create_alembic()

    def create_alembic(self):
        # create the first stamp for alembic
        mkdir = 'mkdir -p {}/ereuse_devicehub/migrations'.format(self.git_clone_path)
        self.c.run(self.cmd(mkdir))
        command = 'cd ereuse_devicehub/; ../../venv/bin/alembic -c alembic.ini stamp head'
        # command = t.format(self.git_clone_path)
        self.c.run(self.cmd_env(command))


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
        self.c.run('apt-get install -qy libapache2-mod-wsgi-py3')

        wsgi_file = 'examples/wsgi.py'
        wsgi_path = os.path.join(self.base_path, 'source')

        f = open('examples/wsgi_template.py')
        wsgi = f.read().format(
            user=self.db_user,
            password=self.db_pass,
            host=self.db_host,
            database=self.db
        )
        f.close()
        f = open(wsgi_file, 'w')
        f.write(wsgi)
        f.close()

        self.c.run('mkdir -p {}'.format(wsgi_path))
        command = 'scp -P {port} {file} {user}@{host}:{path}'.format(
            port=self.c.port,
            file=wsgi_file,
            user=self.c.user,
            host=self.c.host,
            path=wsgi_path
        )
        os.system(command)

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
        self.c.run('mkdir -p /var/log/gunicorn')
        self.c.run('chown {user}.{user} -R /var/log/gunicorn'.format(user=self.user))
        self.gunicorn_conf_services()
        self.gunicorn_conf_socket()

        self.c.run('systemctl daemon-reload')
        self.c.run('systemctl start gunicorn_{}.service'.format(self.name_service))

    def gunicorn_conf_services(self):
        """ Configure gunicorn service file """
        base_file = 'examples/gunicorn/gunicorn_{}.service'.format(self.name_service)
        f = open('examples/gunicorn/gunicorn_template.service')
        gunicorn_service = f.read().format(
            name_service=self.name_service,
            user=self.user,
            base_path=self.base_path,
            domain=self.domain
        )
        f.close()
        f = open(base_file, 'w')
        f.write(gunicorn_service)
        f.close()

        command = 'scp -P {port} {file} {user}@{host}:{path}'.format(
            port=self.c.port,
            file=base_file,
            user=self.c.user,
            host=self.c.host,
            path='/etc/systemd/system/'
        )
        os.system(command)

    def gunicorn_conf_socket(self):
        """ Configure gunicorn socket file """
        base_file = 'examples/gunicorn/gunicorn_{}.socket'.format(self.name_service)
        f = open('examples/gunicorn/gunicorn_template.socket')
        gunicorn_service = f.read().format(
            user=self.user,
            domain=self.domain
        )
        f.close()
        f = open(base_file, 'w')
        f.write(gunicorn_service)
        f.close()

        command = 'scp -P {port} {file} {user}@{host}:{path}'.format(
            port=self.c.port,
            file=base_file,
            user=self.c.user,
            host=self.c.host,
            path='/etc/systemd/system/'
        )
        os.system(command)

    def restart_services(self):
        # XXX. touch the .wsgi file to trigger a reload in mod_wsgi (REQUIRED ON UPDATING NOT ON BOOSTRAP)
        self.c.sudo("systemctl reload apache2")


app = AppDeployment('api.usody.net', 'feature/fabfile-continuous-deployment')
