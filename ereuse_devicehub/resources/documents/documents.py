import csv
import datetime
import enum
import json
import time
import uuid
from collections import OrderedDict
from io import StringIO
from typing import Callable, Iterable, Tuple

import boltons
import flask
import flask_weasyprint
from boltons import urlutils
from flask import current_app as app
from flask import g, make_response, request
from flask.json import jsonify

import ereuse_devicehub.teal.marshmallow
from ereuse_devicehub import auth
from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action import models as evs
from ereuse_devicehub.resources.action.models import Trade
from ereuse_devicehub.resources.deliverynote.models import Deliverynote
from ereuse_devicehub.resources.device import models as devs
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.device.views import DeviceView
from ereuse_devicehub.resources.documents.device_row import (
    ActionRow,
    DeviceRow,
    StockRow,
)
from ereuse_devicehub.resources.enums import SessionType
from ereuse_devicehub.resources.hash_reports import ReportHash, insert_hash, verify_hash
from ereuse_devicehub.resources.lot import LotView
from ereuse_devicehub.resources.lot.models import Lot
from ereuse_devicehub.resources.user.models import Session
from ereuse_devicehub.teal.cache import cache
from ereuse_devicehub.teal.resource import Resource, View


class Format(enum.Enum):
    HTML = 'HTML'
    PDF = 'PDF'


class DocumentView(DeviceView):
    class FindArgs(DeviceView.FindArgs):
        format = ereuse_devicehub.teal.marshmallow.EnumField(Format, missing=None)

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
        args = self.QUERY_PARSER.parse(
            self.find_args, flask.request, locations=('querystring',)
        )
        ids = []
        if 'filter' in request.args:
            filters = json.loads(request.args.get('filter', {}))
            ids = filters.get('ids', [])

        if not ids and not id:
            msg = 'Document must be an ID or UUID.'
            raise ereuse_devicehub.teal.marshmallow.ValidationError(msg)

        if id:
            try:
                id = uuid.UUID(id)
            except ValueError:
                try:
                    ids.append(int(id))
                except ValueError:
                    msg = 'Document must be an ID or UUID.'
                    raise ereuse_devicehub.teal.marshmallow.ValidationError(msg)
                else:
                    query = devs.Device.query.filter(Device.id.in_(ids))
            else:
                query = evs.Action.query.filter_by(id=id)
        else:
            query = devs.Device.query.filter(Device.id.in_(ids))

        # if id:
        #     # todo we assume we can pass both device id and action id
        #     # for certificates... how is it going to end up being?
        #     try:
        #         id = uuid.UUID(id)
        #     except ValueError:
        #         try:
        #             id = int(id)
        #         except ValueError:
        #             raise ereuse_devicehub.teal.marshmallow.ValidationError('Document must be an ID or UUID.')
        #         else:
        #             query = devs.Device.query.filter_by(id=id)
        #     else:
        #         query = evs.Action.query.filter_by(id=id)
        # else:
        #     flask.current_app.auth.requires_auth(lambda: None)()  # todo not nice
        #     query = self.query(args)

        type = urlutils.URL(flask.request.url).path_parts[-2]
        if type == 'erasures':
            template = self.erasure(query)
        if args.get('format') == Format.PDF:
            res = flask_weasyprint.render_pdf(
                flask_weasyprint.HTML(string=template),
                download_filename='{}.pdf'.format(type),
            )
            insert_hash(res.data)
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
        params = {
            'title': 'Device Sanitization',
            'erasures': tuple(erasures()),
            'url_pdf': url_pdf.to_text(),
        }
        return flask.render_template('documents/erasure.html', **params)


class DevicesDocumentView(DeviceView):
    @cache(datetime.timedelta(minutes=1))
    def find(self, args: dict):
        query = self.query(args)
        ids = []
        if 'filter' in request.args:
            filters = json.loads(request.args.get('filter', {}))
            ids = filters.get('ids', [])
        query = self.query(args).filter(Device.id.in_(ids))
        return self.generate_post_csv(query)

    def generate_post_csv(self, query):
        """Get device query and put information in csv format."""
        data = StringIO()
        cw = csv.writer(
            data,
            delimiter=';',
            lineterminator="\n",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )
        first = True
        document_ids = self.get_documents_id()
        for device in query:
            d = DeviceRow(device, document_ids)
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

    def get_documents_id(self):
        # documentIds = {dev_id: document_id, ...}
        deliverys = Deliverynote.query.all()
        documentIds = {x.id: d.document_id for d in deliverys for x in d.lot.devices}
        return documentIds


class ActionsDocumentView(DeviceView):
    @cache(datetime.timedelta(minutes=1))
    def find(self, args: dict):
        filters = json.loads(request.args.get('filter', {}))
        ids = filters.get('ids', [])
        query = self.query(args).filter(Device.id.in_(ids))
        return self.generate_post_csv(query)

    def generate_post_csv(self, query):
        """Get device query and put information in csv format."""
        data = StringIO()
        cw = csv.writer(
            data,
            delimiter=';',
            lineterminator="\n",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )
        first = True
        devs_id = []
        for device in query:
            devs_id.append(device.id)
            for allocate in device.get_metrics():
                d = ActionRow(allocate)
                if first:
                    cw.writerow(d.keys())
                    first = False
                cw.writerow(d.values())
        query_trade = Trade.query.filter(
            Trade.devices.any(Device.id.in_(devs_id))
        ).all()

        lot_id = request.args.get('lot')
        if lot_id and not query_trade:
            lot = Lot.query.filter_by(id=lot_id).one()
            if hasattr(lot, "trade") and lot.trade:
                if g.user in [lot.trade.user_from, lot.trade.user_to]:
                    query_trade = [lot.trade]

        for trade in query_trade:
            data_rows = trade.get_metrics()
            for row in data_rows:
                d = ActionRow(row)
                if first:
                    cw.writerow(d.keys())
                    first = False
                cw.writerow(d.values())

        bfile = data.getvalue().encode('utf-8')
        output = make_response(bfile)
        insert_hash(bfile)
        output.headers[
            'Content-Disposition'
        ] = 'attachment; filename=actions_export.csv'
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
            _lot = LotRow(lot)
            if first:
                cw.writerow(_lot.keys())
                first = False
            cw.writerow(_lot.values())
        bfile = data.getvalue().encode('utf-8')
        output = make_response(bfile)
        insert_hash(bfile)
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
        except Exception:
            self['Description'] = ''


class StockDocumentView(DeviceView):
    # @cache(datetime.timedelta(minutes=1))
    def find(self, args: dict):
        query = (x for x in self.query(args) if x.owner_id == g.user.id)
        return self.generate_post_csv(query)

    def generate_post_csv(self, query):
        """Get device query and put information in csv format."""
        data = StringIO()
        cw = csv.writer(
            data,
            delimiter=';',
            lineterminator="\n",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )
        first = True
        for device in query:
            d = StockRow(device)
            if first:
                cw.writerow(d.keys())
                first = False
            cw.writerow(d.values())
        bfile = data.getvalue().encode('utf-8')
        output = make_response(bfile)
        insert_hash(bfile)
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


class StampsView(View):
    """
    This view render one public ans static page for see the links for to do the check
    of one csv file
    """

    def get_url_path(self):
        url = urlutils.URL(request.url)
        url.normalize()
        url.path_parts = url.path_parts[:-2] + ['check', '']
        return url.to_text()

    def get(self):
        result = ('', '')
        return flask.render_template(
            'documents/stamp.html', rq_url=self.get_url_path(), result=result
        )

    def post(self):
        result = ('', '')
        if 'docUpload' in request.files:
            file_check = request.files['docUpload']
            bad = 'There are no coincidences. The attached file data does not come \
                   from our backend or it has been subsequently modified.'
            ok = '100% coincidence. The attached file contains data 100% existing in \
                  to our backend'
            result = ('Bad', bad)
            mime = [
                'text/csv',
                'application/pdf',
                'text/plain',
                'text/markdown',
                'image/jpeg',
                'image/png',
                'text/html',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.oasis.opendocument.spreadsheet',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword',
            ]
            if file_check.mimetype in mime:
                if verify_hash(file_check):
                    result = ('Ok', ok)

        return flask.render_template(
            'documents/stamp.html', rq_url=self.get_url_path(), result=result
        )


class WbConfDocumentView(DeviceView):
    def get(self, wbtype: str):
        if not wbtype.lower() in ['usodyrate', 'usodywipe']:
            return jsonify('')

        data = {
            'token': self.get_token(),
            'host': app.config['HOST'],
            'inventory': app.config['SCHEMA'],
        }
        data['erase'] = False
        # data['erase'] = True if wbtype == 'usodywipe' else False

        env = flask.render_template('documents/wbSettings.ini', **data)
        output = make_response(env)
        output.headers['Content-Disposition'] = 'attachment; filename=settings.ini'
        output.headers['Content-type'] = 'text/plain'
        return output

    def get_token(self):
        if not g.user.sessions:
            ses = Session(user=g.user)
            db.session.add(ses)
            db.session.commit()

        tk = ''
        now = time.time()
        for s in g.user.sessions:
            if s.type == SessionType.Internal and (s.expired == 0 or s.expired > now):
                tk = s.token
                break

        assert tk != ''

        token = auth.Auth.encode(tk)
        return token


class DocumentDef(Resource):
    __type__ = 'Document'
    SCHEMA = None
    VIEW = None  # We do not want to create default / documents endpoint
    AUTH = False

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder='static',
        static_url_path=None,
        template_folder='templates',
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        super().__init__(
            app,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_commands,
        )
        d = {'id': None}
        get = {'GET'}

        view = DocumentView.as_view('main', definition=self, auth=app.auth)

        # TODO @cayop This two lines never pass
        if self.AUTH:
            view = app.auth.requires_auth(view)

        self.add_url_rule('/erasures/', defaults=d, view_func=view, methods=get)
        self.add_url_rule(
            '/erasures/<{}:{}>'.format(self.ID_CONVERTER.value, self.ID_NAME),
            view_func=view,
            methods=get,
        )

        devices_view = DevicesDocumentView.as_view(
            'devicesDocumentView', definition=self, auth=app.auth
        )
        devices_view = app.auth.requires_auth(devices_view)

        stock_view = StockDocumentView.as_view('stockDocumentView', definition=self)
        stock_view = app.auth.requires_auth(stock_view)

        self.add_url_rule('/devices/', defaults=d, view_func=devices_view, methods=get)

        lots_view = LotsDocumentView.as_view('lotsDocumentView', definition=self)
        lots_view = app.auth.requires_auth(lots_view)
        self.add_url_rule('/lots/', defaults=d, view_func=lots_view, methods=get)

        stock_view = StockDocumentView.as_view(
            'stockDocumentView', definition=self, auth=app.auth
        )
        stock_view = app.auth.requires_auth(stock_view)
        self.add_url_rule('/stock/', defaults=d, view_func=stock_view, methods=get)

        check_view = CheckView.as_view('CheckView', definition=self, auth=app.auth)
        self.add_url_rule('/check/', defaults={}, view_func=check_view, methods=get)

        stamps_view = StampsView.as_view('StampsView', definition=self, auth=app.auth)
        self.add_url_rule(
            '/stamps/', defaults={}, view_func=stamps_view, methods={'GET', 'POST'}
        )

        actions_view = ActionsDocumentView.as_view(
            'ActionsDocumentView', definition=self, auth=app.auth
        )
        actions_view = app.auth.requires_auth(actions_view)
        self.add_url_rule('/actions/', defaults=d, view_func=actions_view, methods=get)

        wbconf_view = WbConfDocumentView.as_view(
            'WbConfDocumentView', definition=self, auth=app.auth
        )
        wbconf_view = app.auth.requires_auth(wbconf_view)
        self.add_url_rule('/wbconf/<string:wbtype>', view_func=wbconf_view, methods=get)
