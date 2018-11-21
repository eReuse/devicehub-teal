import enum
import uuid
from typing import Callable, Iterable, Tuple

import boltons
import flask
import flask_weasyprint
import teal.marshmallow
from boltons import urlutils
from teal.resource import Resource

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device import models as devs
from ereuse_devicehub.resources.device.views import DeviceView
from ereuse_devicehub.resources.event import models as evs


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
            # todo we assume we can pass both device id and event id
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
                query = evs.Event.query.filter_by(id=id)
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
        if self.AUTH:
            view = app.auth.requires_auth(view)
        self.add_url_rule('/erasures/', defaults=d, view_func=view, methods=get)
        self.add_url_rule('/erasures/<{}:{}>'.format(self.ID_CONVERTER.value, self.ID_NAME),
                          view_func=view, methods=get)
