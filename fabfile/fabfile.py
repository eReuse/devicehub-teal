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
        self.inventory = 'dbtest'
        self.tmp = '/tmp/fabfile'

    def def_cmds(self):
        """ Definition of commands in the remote server """
        # General command for ereuse
        base = 'su - {} '.format(self.user)
        self.cmd = (base + '-c \'{}\'').format

        # Command for ereuse into of enviroment
        path_env = (base + ' -c \'cd {}; source ../venv/bin/activate;').format(self.git_clone_path)
        path_env += '{}\''
        self.cmd_env = path_env.format

    def connection(self):
        """ Definition of the connection """
        connect = Connection(self.host)
        connect.user = 'root'
        connect.port = self.port
        return connect

    def bootstrap(self):
        """ Method for to do the first deployment """
        self.install_apt_dependencies()
        self.clone_devicehub_repository()
        self.install_package_requirements()
        self.initialize_database()
        self.setup_wsgi_app()
        self.setup_gunicorn()
        self.setup_letsencrypt()
        self.setup_nginx()

    def upgrade(self):
        """
        Upgrade a running instance of devicehub to the latest version of
        the specified git branch.
        """
        self.upgrade_devicehub_code()
        self.upgrade_package_requirements()
        self.upgrade_database_schema()
        self.restart_services()

    def install_apt_dependencies(self):
        """
        Install debiandependencies than you need for run debicehub
        """
        self.c.run('apt-get update -qy')
        self.c.run('apt-get install -qy {}'.format(' '.join(PACKAGES)))
        self.c.run('su - postgres -c \'psql postgres -c "SELECT version()" | grep PostgreSQL\'')

    def clone_devicehub_repository(self):
        """
        To do the first download of sources from the github repository
        """
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
        """ Installing python packages required """
        self.c.run(self.cmd('python3 -m virtualenv -p python3.7 {}'.format(self.venv_path)))
        self.upgrade_package_requirements()

        command = 'pip install -e {}'.format(self.git_clone_path)
        self.c.run(self.cmd_env(command))
        self.c.run(self.cmd_env('pip install alembic'))

    def upgrade_package_requirements(self):
        """ Upgrade python packages """
        command = self.cmd_env('pip install -r {}/requirements.txt'.format(self.git_clone_path))
        self.c.run(command)
        self.c.run(self.cmd_env('pip install gunicorn==20.0.4'))

    def initialize_database(self):
        """ create database, user and extensions """
        path_orig = '{}/init.sql'.format(self.tmp)
        path_dest = '/var/lib/postgresql'
        f_sql = open('templates/init.sql', 'r')
        sql = f_sql.read().format(user=self.db_user, db=self.db, db_pass=self.db_pass)
        f_sql.close()
        os.system('mkdir -p {}'.format(self.tmp))
        f_sql = open(path_orig, 'w')
        f_sql.write(sql)
        f_sql.close()
        self.scp(path_orig, path_dest)
        command = 'su - postgres -c "psql -f ~/init.sql"'
        self.c.run(command)

        tmpl = open('templates/env.template', 'r')
        env = tmpl.read().format(user=self.db_user, pw=self.db_pass, host=self.host, db=self.db)
        tmpl.close()
        env_domain = '{}/env_{}'.format(self.tmp, self.domain)
        tmpl = open(env_domain, 'w')
        tmpl.write(env)
        tmpl.close()
        self.scp(env_domain, '{}/.env'.format(self.git_clone_path))

        # create schemes in database
        command = 'export dhi={inventory}; dh inv add --common --name {inventory}'
        self.c.run(self.cmd_env(command.format(inventory=self.inventory)))
        self.create_alembic()
        os.system('rm -fr {}'.format(self.tmp))
        self.c.run('rm -fr {}/init.sql'.format(path_dest))

    def create_alembic(self):
        """ create the first stamp for alembic """
        mkdir = 'mkdir -p {}/ereuse_devicehub/migrations'.format(self.git_clone_path)
        self.c.run(self.cmd(mkdir))
        command = 'cd ereuse_devicehub/; ../../venv/bin/alembic -c alembic.ini stamp head'
        self.c.run(self.cmd_env(command))


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

    def setup_wsgi_app(self):
        """ Installing wsgi file """
        wsgi_path = os.path.join(self.base_path, 'source')
        self.c.run('mkdir -p {}'.format(wsgi_path))
        self.scp('templates/wsgi.py', wsgi_path)

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
        os.system('mkdir -p {}'.format(self.tmp))
        base_file = '{}/gunicorn_{}.service'.format(self.tmp, self.name_service)
        fgun = open('templates/gunicorn/gunicorn_template.service')
        gunicorn_service = fgun.read().format(
            name_service=self.name_service,
            user=self.user,
            base_path=self.base_path,
            domain=self.domain
        )
        fgun.close()
        fgun = open(base_file, 'w')
        fgun.write(gunicorn_service)
        fgun.close()
        self.scp(base_file, '/etc/systemd/system/')
        self.c.run('systemctl enable gunicorn_{}.service'.format(self.name_service))
        os.system('rm -fr {}'.format(self.tmp))

    def gunicorn_conf_socket(self):
        """ Configure gunicorn socket file """
        os.system('mkdir -p {}'.format(self.tmp))
        base_file = '{}/gunicorn_{}.socket'.format(self.tmp, self.name_service)
        fgun = open('templates/gunicorn/gunicorn_template.socket')
        gunicorn_service = fgun.read().format(
            user=self.user,
            domain=self.domain
        )
        fgun.close()
        fgun = open(base_file, 'w')
        fgun.write(gunicorn_service)
        fgun.close()
        self.scp(base_file, '/etc/systemd/system/')
        self.c.run('systemctl enable gunicorn_{}.socket'.format(self.name_service))
        os.system('rm -fr {}'.format(self.tmp))

    def setup_nginx(self):
        """Configure ngnix & restart service"""
        self.c.run('apt-get install -qy nginx')
        self.nginx_conf_site()
        self.c.run('systemctl restart nginx')

    def nginx_conf_site(self):
        """ Configure gunicorn socket file """
        os.system('mkdir -p {}'.format(self.tmp))
        file_name = '00_{}.conf'.format(self.domain)
        base_file = '{}/{}'.format(self.tmp, file_name)
        fninx = open('templates/nginx/site_template.conf')
        site = fninx.read().format(
            domain=self.domain
        )
        fninx.close()
        fninx = open(base_file, 'w')
        fninx.write(site)
        fninx.close()
        self.scp(base_file, '/etc/nginx/sites-available/')
        self.c.run('ln -sf /etc/nginx/sites-available/{} /etc/nginx/sites-enabled/'.format(
            file_name))
        self.c.run('nginx -t')
        os.system('rm -fr {}'.format(self.tmp))

    def setup_letsencrypt(self):
        """ Install letsencrypt and add options for use it in nginx """
        self.c.run('apt-get install -qy letsencrypt')
        file_input = 'templates/letsencrypt/options-ssl-nginx.conf'
        file_output = '/etc/letsencrypt/options-ssl-nginx.conf'
        self.scp(file_input, file_output)

    def scp(self, file_in, path_out):
        """ Comand for use scp to the server of deployment """
        command = 'scp -P {port} {file} {user}@{host}:{path}'.format(
            port=self.c.port,
            file=file_in,
            user=self.c.user,
            host=self.c.host,
            path=path_out
        )
        os.system(command)

    def upgrade_devicehub_code(self):
        """ Update code using git pull """
        params = {
            'path': self.git_clone_path,
        }
        result = self.c.run(self.cmd('cd {path} && git pull --ff-only'.format(**params)))
        if result.failed:
            raise RuntimeError("Error retrieving latest devicehub code: {}".format(result.stderr))

    def upgrade_database_schema(self):
        """
        Run the following command for upgrade the database structure
        """
        command = 'alembic -x inventory={inventory} upgrade head'.format(inventory=self.inventory)
        self.c.run(self.cmd_env(command))

    def restart_services(self):
        """ Restarting gunicorn is enough for the restart the services """
        stop_gunicorn_sock = "systemctl stop gunicorn_{domain}.socket".format(
            domain=self.name_service)
        stop_gunicorn_service = "systemctl stop gunicorn_{domain}.service".format(
            domain=self.name_service)
        start_gunicorn_service = "systemctl start gunicorn_{domain}.service".format(
            domain=self.name_service)

        self.c.run(stop_gunicorn_sock)
        self.c.run(stop_gunicorn_service)
        self.c.run(start_gunicorn_service)


app = AppDeployment('api.usody.net', 'feature/fabfile-continuous-deployment')
