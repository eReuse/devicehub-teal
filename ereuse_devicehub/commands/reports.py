import csv

# import click_spinner
# import ereuse_utils.cli
from io import StringIO

from ereuse_devicehub.resources.action import models as evs
from ereuse_devicehub.resources.device.models import Placeholder
from ereuse_devicehub.resources.documents.device_row import InternalStatsRow

# import click


class Report:
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        short_help = 'Creates reports devices and users.'
        self.app.cli.command('report', short_help=short_help)(self.run)

    def run(self):
        stats = InternalStatsView()
        stats.print()


class InternalStatsView:
    def print(self):
        query = evs.Action.query.filter(
            evs.Action.type.in_(
                (
                    'Snapshot',
                    'Live',
                    'Allocate',
                    'Deallocate',
                    'EraseBasic',
                    'EraseSectors',
                )
            )
        )
        return self.generate_post_csv(query)

    def generate_post_csv(self, query):
        data = StringIO()
        cw = csv.writer(data, delimiter=';', lineterminator="\n", quotechar='"')
        cw.writerow(InternalStatsRow('', "2000-1", []).keys())

        for row in self.get_rows(query):
            cw.writerow(row)

        return print(data.getvalue())

    def get_rows(self, query):
        d = {}
        dd = {}
        for ac in query:
            create = '{}-{}'.format(ac.created.year, ac.created.month)
            user = ac.author.email

            if user not in d:
                d[user] = {}
                dd[user] = {}
            if create not in d[user]:
                d[user][create] = []
                dd[user][create] = None
            d[user][create].append(ac)

        for user, createds in d.items():
            for create, actions in createds.items():
                r = InternalStatsRow(user, create, actions)
                dd[user][create] = r

        return self.get_placeholders(dd)

    def get_placeholders(self, dd):

        for p in Placeholder.query.all():
            create = '{}-{}'.format(p.created.year, p.created.month)
            user = p.owner.email

            if user not in dd:
                dd[user] = {}

            if create not in dd[user]:
                dd[user][create] = None

            if not dd[user][create]:
                dd[user][create] = InternalStatsRow(user, create, [])

            dd[user][create]['Placeholders'] += 1

        rows = []
        for user, createds in dd.items():
            for create, row in createds.items():
                rows.append(row.values())
        return rows
