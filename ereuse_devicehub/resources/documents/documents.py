import csv
import datetime
import enum
import uuid
from collections import OrderedDict
from io import StringIO
from typing import Callable, Iterable, Tuple

import boltons
import flask
import flask_weasyprint
import teal.marshmallow
from boltons import urlutils
from flask import make_response, g, request
from flask.json import jsonify
from teal.cache import cache
from teal.resource import Resource, View

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action import models as evs
from ereuse_devicehub.resources.device import models as devs
from ereuse_devicehub.resources.device.views import DeviceView
from ereuse_devicehub.resources.documents.device_row import DeviceRow, StockRow
from ereuse_devicehub.resources.lot import LotView
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.hash_reports import insert_hash, ReportHash


class Format(enum.Enum):
    HTML = 'HTML'
    PDF = 'PDF'


class DocumentView(DeviceView):
    class FindArgs(DeviceView.FindArgs):
        format = teal.marshmallow.EnumField(Format, missing=None)

    def get(self, id):
        """Get a collection of resources or a specific one.
        ---
        parameters:
        - name: id
          in: path
          description: The identifier of the resource.
          type: string
          required: false
        responses:
          200:
            description: Return the collection or the specific one.
        """
        args = self.QUERY_PARSER.parse(self.find_args,
                                       flask.request,
                                       locations=('querystring',))
        if id:
            # todo we assume we can pass both device id and action id
            # for certificates... how is it going to end up being?
            try:
                id = uuid.UUID(id)
            except ValueError:
                try:
                    id = int(id)
                except ValueError:
                    raise teal.marshmallow.ValidationError('Document must be an ID or UUID.')
                else:
                    query = devs.Device.query.filter_by(id=id)
            else:
                query = evs.Action.query.filter_by(id=id)
        else:
            flask.current_app.auth.requires_auth(lambda: None)()  # todo not nice
            query = self.query(args)

        type = urlutils.URL(flask.request.url).path_parts[-2]
        if type == 'erasures':
            template = self.erasure(query)
        if args.get('format') == Format.PDF:
            res = flask_weasyprint.render_pdf(
                flask_weasyprint.HTML(string=template), download_filename='{}.pdf'.format(type)
            )
        else:
            res = flask.make_response(template)
        return res

    @staticmethod
    def erasure(query: db.Query):
        def erasures():
            for model in query:
                if isinstance(model, devs.Computer):
                    for erasure in model.privacy:
                        yield erasure
                elif isinstance(model, devs.DataStorage):
                    erasure = model.privacy
                    if erasure:
                        yield erasure
                else:
                    assert isinstance(model, evs.EraseBasic)
                    yield model

        url_pdf = boltons.urlutils.URL(flask.request.url)
        url_pdf.query_params['format'] = 'PDF'
        url_web = boltons.urlutils.URL(flask.request.url)
        url_web.query_params['format'] = 'HTML'
        params = {
            'title': 'Erasure Certificate',
            'erasures': tuple(erasures()),
            'url_pdf': url_pdf.to_text(),
            'url_web': url_web.to_text()
        }
        return flask.render_template('documents/erasure.html', **params)


class DevicesDocumentView(DeviceView):
    @cache(datetime.timedelta(minutes=1))
    def find(self, args: dict):
        query = (x for x in self.query(args) if x.owner_id == g.user.id)
        return self.generate_post_csv(query)

    def generate_post_csv(self, query):
        """Get device query and put information in csv format."""
        data = StringIO()
        cw = csv.writer(data, delimiter=';', lineterminator="\n", quotechar='"')
        first = True
        for device in query:
            d = DeviceRow(device)
            if first:
                cw.writerow(d.keys())
                first = False
            cw.writerow(d.values())
        bfile = data.getvalue().encode('utf-8')
        output = make_response(bfile)
        insert_hash(bfile)
        output.headers['Content-Disposition'] = 'attachment; filename=export.csv'
        output.headers['Content-type'] = 'text/csv'
        return output


class LotsDocumentView(LotView):
    def find(self, args: dict):
        query = (x for x in self.query(args) if x.owner_id == g.user.id)
        return self.generate_lots_csv(query)

    def generate_lots_csv(self, query):
        """Get lot query and put information in csv format."""
        data = StringIO()
        cw = csv.writer(data)
        first = True
        for lot in query:
            l = LotRow(lot)
            if first:
                cw.writerow(l.keys())
                first = False
            cw.writerow(l.values())
        output = make_response(data.getvalue())
        output.headers['Content-Disposition'] = 'attachment; filename=lots-info.csv'
        output.headers['Content-type'] = 'text/csv'
        return output


class LotRow(OrderedDict):
    def __init__(self, lot: Lot) -> None:
        super().__init__()
        self.lot = lot
        # General information about lot
        self['Id'] = lot.id.hex
        self['Name'] = lot.name
        self['Registered in'] = format(lot.created, '%c')
        try:
            self['Description'] = lot.description
        except:
            self['Description'] = ''


class StockDocumentView(DeviceView):
    # @cache(datetime.timedelta(minutes=1))
    def find(self, args: dict):
        query = (x for x in self.query(args) if x.owner_id == g.user.id)
        return self.generate_post_csv(query)

    def generate_post_csv(self, query):
        """Get device query and put information in csv format."""
        data = StringIO()
        cw = csv.writer(data)
        first = True
        for device in query:
            d = StockRow(device)
            if first:
                cw.writerow(d.keys())
                first = False
            cw.writerow(d.values())
        output = make_response(data.getvalue())
        output.headers['Content-Disposition'] = 'attachment; filename=devices-stock.csv'
        output.headers['Content-type'] = 'text/csv'
        return output


class CheckView(View):
    model = ReportHash

    def get(self):
        qry = dict(request.values)
        hash3 = qry.get('hash')

        result = False
        if hash3 and ReportHash.query.filter_by(hash3=hash3).count():
            result = True
        return jsonify(result)


class DocumentDef(Resource):
    __type__ = 'Document'
    SCHEMA = None
    VIEW = None  # We do not want to create default / documents endpoint
    AUTH = False

    def __init__(self, app,
                 import_name=__name__,
                 static_folder='static',
                 static_url_path=None,
                 template_folder='templates',
                 url_prefix=None,
                 subdomain=None,
                 url_defaults=None,
                 root_path=None,
                 cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path, cli_commands)
        d = {'id': None}
        get = {'GET'}

        view = DocumentView.as_view('main', definition=self, auth=app.auth)

        # TODO @cayop This two lines never pass
        if self.AUTH:
            view = app.auth.requires_auth(view)

        self.add_url_rule('/erasures/', defaults=d, view_func=view, methods=get)
        self.add_url_rule('/erasures/<{}:{}>'.format(self.ID_CONVERTER.value, self.ID_NAME),
                          view_func=view, methods=get)

        devices_view = DevicesDocumentView.as_view('devicesDocumentView',
                                                   definition=self,
                                                   auth=app.auth)
        devices_view = app.auth.requires_auth(devices_view)

        stock_view = StockDocumentView.as_view('stockDocumentView', definition=self)
        stock_view = app.auth.requires_auth(stock_view)

        self.add_url_rule('/devices/', defaults=d, view_func=devices_view, methods=get)

        lots_view = LotsDocumentView.as_view('lotsDocumentView', definition=self)
        lots_view = app.auth.requires_auth(lots_view)
        self.add_url_rule('/lots/', defaults=d, view_func=lots_view, methods=get)

        stock_view = StockDocumentView.as_view('stockDocumentView', definition=self, auth=app.auth)
        stock_view = app.auth.requires_auth(stock_view)
        self.add_url_rule('/stock/', defaults=d, view_func=stock_view, methods=get)

        check_view = CheckView.as_view('CheckView', definition=self, auth=app.auth)
        self.add_url_rule('/check/', defaults={}, view_func=check_view, methods=get)
