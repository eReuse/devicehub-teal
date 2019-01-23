import os

import click.testing
import flask.cli

from ereuse_devicehub.config import DevicehubConfig
from ereuse_devicehub.devicehub import Devicehub


class DevicehubGroup(flask.cli.FlaskGroup):
    CONFIG = DevicehubConfig

    def main(self, *args, **kwargs):
        # todo this should be taken as an argument for the cli
        inventory = os.environ.get('dhi')
        if not inventory:
            raise ValueError('Please do "export dhi={inventory}"')
        self.create_app = self.create_app_factory(inventory)
        return super().main(*args, **kwargs)

    @staticmethod
    def create_app_factory(inventory):
        return lambda: Devicehub(inventory)


@click.group(cls=DevicehubGroup)
def cli():
    pass
