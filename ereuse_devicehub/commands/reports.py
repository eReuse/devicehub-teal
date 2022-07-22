import csv

# import click
# import click_spinner
# import ereuse_utils.cli
from io import StringIO

from ereuse_devicehub.resources.action import models as evs
from ereuse_devicehub.resources.documents.device_row import InternalStatsRow


class Report:

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.app.cli.command('report', short_help='Creates reports devices and users.')(
            self.run
        )

    def run(self):
        stats = InternalStatsView()
        stats.print()


class InternalStatsView:
    def print(self):
        query = evs.Action.query.filter(
            evs.Action.type.in_(('Snapshot', 'Live', 'Allocate', 'Deallocate')))
        return self.generate_post_csv(query)

    def generate_post_csv(self, query):
        d = {}
        for ac in query:
            create = '{}-{}'.format(ac.created.year, ac.created.month)
            user = ac.author.email

            if user not in d:
                d[user] = {}
            if create not in d[user]:
                d[user][create] = []
            d[user][create].append(ac)

        data = StringIO()
        cw = csv.writer(data, delimiter=';', lineterminator="\n", quotechar='"')
        cw.writerow(InternalStatsRow('', "2000-1", []).keys())
        for user, createds in d.items():
            for create, actions in createds.items():
                cw.writerow(InternalStatsRow(user, create, actions).values())

        return print(data.getvalue())
