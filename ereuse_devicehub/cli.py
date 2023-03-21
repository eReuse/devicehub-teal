import os

import click.testing
import flask.cli
import ereuse_devicehub.ereuse_utils

from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.devicehub import Devicehub

import sys

sys.ps1 = '\001\033[92m\002>>> \001\033[0m\002'
sys.ps2 = '\001\033[94m\002... \001\033[0m\002'

import os, readline, atexit

history_file = os.path.join(os.environ['HOME'], '.python_history')
try:
    readline.read_history_file(history_file)
except IOError:
    pass
readline.parse_and_bind("tab: complete")
readline.parse_and_bind('"\e[5~": history-search-backward')
readline.parse_and_bind('"\e[6~": history-search-forward')
readline.parse_and_bind('"\e[5C": forward-word')
readline.parse_and_bind('"\e[5D": backward-word')
readline.parse_and_bind('"\e\e[C": forward-word')
readline.parse_and_bind('"\e\e[D": backward-word')
readline.parse_and_bind('"\e[1;5C": forward-word')
readline.parse_and_bind('"\e[1;5D": backward-word')
readline.set_history_length(100000)
atexit.register(readline.write_history_file, history_file)


class DevicehubGroup(flask.cli.FlaskGroup):
    # todo users cannot make cli to use a custom db this way!
    CONFIG = DevicehubConfig

    def main(self, *args, **kwargs):
        # todo this should be taken as an argument for the cli
        inventory = os.environ.get('dhi')
        if not inventory:
            raise ValueError('Please do "export dhi={inventory}"')
        self.create_app = self.create_app_factory(inventory)
        return super().main(*args, **kwargs)

    @classmethod
    def create_app_factory(cls, inventory):
        return lambda: Devicehub(inventory, config=cls.CONFIG())


def get_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(
        'Devicehub {}'.format(
            ereuse_devicehub.ereuse_utils.version('ereuse-devicehub')
        ),
        color=ctx.color,
    )
    flask.cli.get_version(ctx, param, value)


@click.option(
    '--version',
    help='Devicehub version.',
    expose_value=False,
    callback=get_version,
    is_flag=True,
    is_eager=True,
)
@click.group(
    cls=DevicehubGroup,
    context_settings=Devicehub.cli_context_settings,
    add_version_option=False,
    help="""Manages the Devicehub of the inventory {}.

            Use 'export dhi=xx' to set the inventory that this CLI
            manages. For example 'export dhi=db1' and then executing
            'dh tag add' adds a tag in the db1 database. Operations
            that affect the common database (like creating an user)
            are not affected by this.
             """.format(
        os.environ.get('dhi')
    ),
)
def cli():
    pass
