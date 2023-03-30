import inspect
from typing import Type

import click_spinner
import flask_cors
from anytree import Node
from apispec import APISpec
from click import option
from flask import Flask, jsonify
from flask.globals import _app_ctx_stack
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException, UnprocessableEntity

import ereuse_devicehub.ereuse_utils
from ereuse_devicehub.ereuse_utils import ensure_utf8
from ereuse_devicehub.teal.auth import Auth
from ereuse_devicehub.teal.cli import TealCliRunner
from ereuse_devicehub.teal.client import Client
from ereuse_devicehub.teal.config import Config as ConfigClass
from ereuse_devicehub.teal.db import SchemaSQLAlchemy
from ereuse_devicehub.teal.json_util import TealJSONEncoder
from ereuse_devicehub.teal.request import Request
from ereuse_devicehub.teal.resource import Converters, LowerStrConverter, Resource


class Teal(Flask):
    """
    An opinionated REST and JSON first server built on Flask using
    MongoDB and Marshmallow.
    """

    test_client_class = Client
    request_class = Request
    json_encoder = TealJSONEncoder
    cli_context_settings = {'help_option_names': ('-h', '--help')}
    test_cli_runner_class = TealCliRunner

    def __init__(
        self,
        config: ConfigClass,
        db: SQLAlchemy,
        schema: str = None,
        import_name=__name__.split('.')[0],
        static_url_path=None,
        static_folder='static',
        static_host=None,
        host_matching=False,
        subdomain_matching=False,
        template_folder='templates',
        instance_path=None,
        instance_relative_config=False,
        root_path=None,
        use_init_db=True,
        Auth: Type[Auth] = Auth,
    ):
        """

        :param config:
        :param db:
        :param schema: A string describing the main PostgreSQL's schema.
                      ``None`` disables this functionality.
                      If you use a factory of apps (for example by using
                      :func:`teal.teal.prefixed_database_factory`) and then set this
                      value differently per each app (as each app has a separate config)
                      you effectively create a `multi-tenant app <https://
                      news.ycombinator.com/item?id=4268792>`_.
                      Your models by default will be created in this ``SCHEMA``,
                      unless you set something like::

                          class User(db.Model):
                              __table_args__ = {'schema': 'users'}

                      In which case this will be created in the ``users`` schema.
                      Schemas are interesting over having multiple databases (i.e. using
                      flask-sqlalchemy's data binding) because you can have relationships
                      between them.

                      Note that this only works with PostgreSQL.
        :param import_name:
        :param static_url_path:
        :param static_folder:
        :param static_host:
        :param host_matching:
        :param subdomain_matching:
        :param template_folder:
        :param instance_path:
        :param instance_relative_config:
        :param root_path:
        :param Auth:
        """
        self.schema = schema
        ensure_utf8(self.__class__.__name__)
        super().__init__(
            import_name,
            static_url_path,
            static_folder,
            static_host,
            host_matching,
            subdomain_matching,
            template_folder,
            instance_path,
            instance_relative_config,
            root_path,
        )
        self.config.from_object(config)
        flask_cors.CORS(self)
        # Load databases
        self.auth = Auth()
        self.url_map.converters[Converters.lower.name] = LowerStrConverter
        self.load_resources()
        self.register_error_handler(HTTPException, self._handle_standard_error)
        self.register_error_handler(ValidationError, self._handle_validation_error)
        self.db = db
        db.init_app(self)
        if use_init_db:
            self.cli.command('init-db', context_settings=self.cli_context_settings)(
                self.init_db
            )
        self.spec = None  # type: APISpec
        self.apidocs()

    # noinspection PyAttributeOutsideInit
    def load_resources(self):
        self.resources = {}
        """
        The resources definitions loaded on this App, referenced by their
        type name.
        """
        self.tree = {}
        """
        A tree representing the hierarchy of the instances of
        ResourceDefinitions. ResourceDefinitions use these nodes to
        traverse their hierarchy.

        Do not use the normal python class hierarchy as it is global,
        thus unreliable if you run different apps with different
        schemas (for example, an extension that is only added on the
        third app adds a new type of user).
        """
        for ResourceDef in self.config['RESOURCE_DEFINITIONS']:
            resource_def = ResourceDef(self)  # type: Resource
            self.register_blueprint(resource_def)

            if resource_def.cli_commands:

                @self.cli.group(
                    resource_def.cli_name,
                    context_settings=self.cli_context_settings,
                    short_help='{} management.'.format(resource_def.type),
                )
                def dummy_group():
                    pass

            for (
                cli_command,
                *args,
            ) in resource_def.cli_commands:  # Register CLI commands
                # todo cli commands with multiple arguments end-up reversed
                # when teal has been executed multiple times (ex. testing)
                # see _param_memo func in click package
                dummy_group.command(*args)(cli_command)

            # todo should we use resource_def.name instead of type?
            # are we going to have collisions? (2 resource_def -> 1 schema)
            self.resources[resource_def.type] = resource_def
            self.tree[resource_def.type] = Node(resource_def.type)
        # Link tree nodes between them
        for _type, node in self.tree.items():
            resource_def = self.resources[_type]
            _, Parent, *superclasses = inspect.getmro(resource_def.__class__)
            if Parent is not Resource:
                node.parent = self.tree[Parent.type]

    @staticmethod
    def _handle_standard_error(e: HTTPException):
        """
        Handles HTTPExceptions by transforming them to JSON.
        """
        try:
            response = jsonify(e)
            response.status_code = e.code
        except (AttributeError, TypeError) as e:
            code = getattr(e, 'code', 500)
            response = jsonify(
                {'message': str(e), 'code': code, 'type': e.__class__.__name__}
            )
            response.status_code = code
        return response

    @staticmethod
    def _handle_validation_error(e: ValidationError):
        data = {
            'message': e.messages,
            'code': UnprocessableEntity.code,
            'type': e.__class__.__name__,
        }
        response = jsonify(data)
        response.status_code = UnprocessableEntity.code
        return response

    @option(
        '--erase/--no-erase',
        default=False,
        help='Delete all contents from the database (including common schemas)?',
    )
    @option(
        '--exclude-schema',
        default=None,
        help='Schema to exclude creation (and deletion if --erase is set). '
        'Required the SchemaSQLAlchemy.',
    )
    def init_db(self, erase: bool = False, exclude_schema=None):
        """
        Initializes a database from scratch,
        creating tables and needed resources.

        Note that this does not create the database per se.

        If executing this directly, remember to use an app_context.

        Resources can hook functions that will be called when this
        method executes, by subclassing :meth:`teal.resource.
        Resource.load_resource`.
        """
        assert _app_ctx_stack.top, 'Use an app context.'
        print('Initializing database...'.ljust(30), end='')
        with click_spinner.spinner():
            if erase:
                if exclude_schema:  # Using then a schema teal sqlalchemy
                    assert isinstance(self.db, SchemaSQLAlchemy)
                    self.db.drop_schema()
                else:  # using regular flask sqlalchemy
                    self.db.drop_all()
            self._init_db(exclude_schema)
            self._init_resources()
            self.db.session.commit()
        print('done.')

    def _init_db(self, exclude_schema=None) -> bool:
        """Where the database is initialized. You can override this.

        :return: A flag stating if the database has been created (can
        be False in case check is True and the schema already
        exists).
        """
        if exclude_schema:  # Using then a schema teal sqlalchemy
            assert isinstance(self.db, SchemaSQLAlchemy)
            self.db.create_all(exclude_schema=exclude_schema)
        else:  # using regular flask sqlalchemy
            self.db.create_all()
        return True

    def _init_resources(self, **kw):
        for resource in self.resources.values():
            resource.init_db(self.db, **kw)

    def apidocs(self):
        """Apidocs configuration and generation."""
        self.spec = APISpec(
            plugins=(
                'apispec.ext.flask',
                'apispec.ext.marshmallow',
            ),
            **self.config.get_namespace('API_DOC_CONFIG_'),
        )
        for name, resource in self.resources.items():
            if resource.SCHEMA:
                self.spec.definition(
                    name,
                    schema=resource.SCHEMA,
                    extra_fields=self.config.get_namespace('API_DOC_CLASS_'),
                )
        self.add_url_rule('/apidocs', view_func=self.apidocs_endpoint)

    def apidocs_endpoint(self):
        """An endpoint that prints a JSON OpenApi 2.0 specification."""
        if not getattr(self, '_apidocs', None):
            # We are forced to to this under a request context
            for path, view_func in self.view_functions.items():
                if path != 'static':
                    self.spec.add_path(view=view_func)
            self._apidocs = self.spec.to_dict()
        return jsonify(self._apidocs)


class DumpeableHTTPException(ereuse_devicehub.ereuse_utils.Dumpeable):
    """Exceptions that inherit this class will be able to dump
    to dicts and JSONs.
    """

    def dump(self):
        # todo this is heavily ad-hoc and should be more generic
        value = super().dump()
        value['type'] = self.__class__.__name__
        value['code'] = self.code
        value.pop('exc', None)
        value.pop('response', None)
        if 'data' in value:
            value['fields'] = value['data']['messages']
            del value['data']
        if 'message' not in value:
            value['message'] = value.pop('description', str(self))
        return value


# Add dump capacity to Werkzeug's HTTPExceptions
HTTPException.__bases__ = HTTPException.__bases__ + (DumpeableHTTPException,)
