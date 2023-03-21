from enum import Enum
from typing import Callable, Iterable, Iterator, Tuple, Type, Union

import inflection
from anytree import PreOrderIter
from boltons.typeutils import classproperty, issubclass
from ereuse_devicehub.ereuse_utils.naming import Naming
from flask import Blueprint, current_app, g, request, url_for
from flask.json import jsonify
from flask.views import MethodView
from marshmallow import Schema as MarshmallowSchema
from marshmallow import SchemaOpts as MarshmallowSchemaOpts
from marshmallow import ValidationError, post_dump, pre_load, validates_schema
from werkzeug.exceptions import MethodNotAllowed
from werkzeug.routing import UnicodeConverter

from ereuse_devicehub.teal import db, query


class SchemaOpts(MarshmallowSchemaOpts):
    """
    Subclass of Marshmallow's SchemaOpts that provides
    options for Teal's schemas.
    """

    def __init__(self, meta, ordered=False):
        super().__init__(meta, ordered)
        self.PREFIX = meta.PREFIX


class Schema(MarshmallowSchema):
    """
    The definition of the fields of a resource.
    """

    OPTIONS_CLASS = SchemaOpts

    class Meta:
        PREFIX = None
        """Optional. A prefix for the type; ex. devices:Computer."""

    # noinspection PyMethodParameters
    @classproperty
    def t(cls: Type['Schema']) -> str:
        """The type for this schema, auto-computed from its name."""
        name, *_ = cls.__name__.split('Schema')
        return Naming.new_type(name, cls.Meta.PREFIX)

    # noinspection PyMethodParameters
    @classproperty
    def resource(cls: Type['Schema']) -> str:
        """The resource name of this schema."""
        return Naming.resource(cls.t)

    @validates_schema(pass_original=True)
    def check_unknown_fields(self, _, original_data: dict):
        """
        Raises a validationError when user sends extra fields.

        From `Marshmallow docs<http://marshmallow.readthedocs.io/en/
        latest/extending.html#validating-original-input-data>`_.
        """
        unknown_fields = set(original_data) - set(
            f.data_key or n for n, f in self.fields.items()
        )
        if unknown_fields:
            raise ValidationError('Unknown field', unknown_fields)

    @validates_schema(pass_original=True)
    def check_dump_only(self, _, orig_data: dict):
        """
        Raises a ValidationError if the user is submitting
        'read-only' fields.
        """
        # Note that validates_schema does not execute when dumping
        dump_only_fields = (
            name for name, field in self.fields.items() if field.dump_only
        )
        non_writable = set(orig_data).intersection(dump_only_fields)
        if non_writable:
            raise ValidationError('Non-writable field', non_writable)

    @pre_load
    @post_dump
    def remove_none_values(self, data: dict) -> dict:
        """
        Skip from dumping and loading values that are None.

        A value that is None will be the same as a value that has not
        been set.

        `From here <https://github.com/marshmallow-code/marshmallow/
        issues/229#issuecomment-134387999>`_.
        """
        # Will I always want this?
        # maybe this could be a setting in the future?
        return {key: value for key, value in data.items() if value is not None}

    def dump(
        self,
        model: Union['db.Model', Iterable['db.Model']],
        many=None,
        update_fields=True,
        nested=None,
        polymorphic_on='t',
    ):
        """
        Like marshmallow's dump but with nested resource support and
        it only works for Models.

        This can load model relationships up to ``nested`` level. For
        example, if ``nested`` is ``1`` and we pass in a model of
        ``User`` that has a relationship with a table of ``Post``, it
        will load ``User`` and ``User.posts`` with all posts objects
        populated, but it won't load relationships inside the
        ``Post`` object. If, at the same time the ``Post`` has
        an ``author`` relationship with ``author_id`` being the FK,
        ``user.posts[n].author`` will be the value of ``author_id``.

        Define nested fields with the
        :class:`ereuse_devicehub.teal.marshmallow.NestedOn`

        This method requires an active application context as it needs
        to store some stuff in ``g``.

        :param nested: How many layers of nested relationships to load?
                       By default only loads 1 nested relationship.
        """
        from ereuse_devicehub.teal.marshmallow import NestedOn

        if nested is not None:
            setattr(g, NestedOn.NESTED_LEVEL, 0)
            setattr(g, NestedOn.NESTED_LEVEL_MAX, nested)
        if many:
            # todo this breaks with normal dicts. Maybe this should go
            # in NestedOn in the same way it happens when loading
            if isinstance(model, dict):
                return super().dump(model, update_fields=update_fields)
            else:
                return [
                    self._polymorphic_dump(o, update_fields, polymorphic_on)
                    for o in model
                ]

        else:
            if isinstance(model, dict):
                return super().dump(model, update_fields=update_fields)
            else:
                return self._polymorphic_dump(model, update_fields, polymorphic_on)

    def _polymorphic_dump(self, obj: 'db.Model', update_fields, polymorphic_on='t'):
        schema = current_app.resources[getattr(obj, polymorphic_on)].schema
        if schema.t != self.t:
            return super(schema.__class__, schema).dump(obj, False, update_fields)
        else:
            return super().dump(obj, False, update_fields)

    def jsonify(
        self,
        model: Union['db.Model', Iterable['db.Model']],
        nested=1,
        many=False,
        update_fields: bool = True,
        polymorphic_on='t',
        **kw,
    ) -> str:
        """
        Like flask's jsonify but with model / marshmallow schema
        support.

        :param nested: How many layers of nested relationships to load?
                       By default only loads 1 nested relationship.
        """
        return jsonify(self.dump(model, many, update_fields, nested, polymorphic_on))


class View(MethodView):
    """
    A REST interface for resources.
    """

    QUERY_PARSER = query.NestedQueryFlaskParser()

    class FindArgs(MarshmallowSchema):
        """
        Allowed arguments for the ``find``
        method (GET collection) endpoint
        """

    def __init__(self, definition: 'Resource', **kw) -> None:
        self.resource_def = definition
        """The ResourceDefinition tied to this view."""
        self.schema = None  # type: Schema
        """The schema tied to this view."""
        self.find_args = self.FindArgs()
        super().__init__()

    def dispatch_request(self, *args, **kwargs):
        # This is unique for each view call
        self.schema = g.schema
        """
        The default schema in this resource. 
        Added as an attr for commodity; you can always use g.schema.
        """
        return super().dispatch_request(*args, **kwargs)

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
        if id:
            response = self.one(id)
        else:
            args = self.QUERY_PARSER.parse(
                self.find_args, request, locations=('querystring',)
            )
            response = self.find(args)
        return response

    def one(self, id):
        """GET one specific resource (ex. /cars/1)."""
        raise MethodNotAllowed()

    def find(self, args: dict):
        """GET a list of resources (ex. /cars)."""
        raise MethodNotAllowed()

    def post(self):
        raise MethodNotAllowed()

    def delete(self, id):
        raise MethodNotAllowed()

    def put(self, id):
        raise MethodNotAllowed()

    def patch(self, id):
        raise MethodNotAllowed()


class Converters(Enum):
    """An enumeration of available URL converters."""

    string = 'string'
    int = 'int'
    float = 'float'
    path = 'path'
    any = 'any'
    uuid = 'uuid'
    lower = 'lower'


class LowerStrConverter(UnicodeConverter):
    """Like StringConverter but lowering the string."""

    def to_python(self, value):
        return super().to_python(value).lower()


class Resource(Blueprint):
    """
    Main resource class. Defines the schema, views,
    authentication, database and collection of a resource.

    A ``ResourceDefinition`` is a Flask
    :class:`flask.blueprints.Blueprint` that provides everything
    needed to set a REST endpoint.
    """

    VIEW = None  # type: Type[View]
    """
    Resource view linked to this definition or None.
    If none, this resource does not generate any view.
    """
    SCHEMA = Schema  # type: Type[Schema]
    """The Schema that validates a submitting resource at the entry point."""
    AUTH = False
    """
    If true, authentication is required for all the endpoints of this 
    resource defined in ``VIEW``.
    """
    ID_NAME = 'id'
    """
    The variable name for GET *one* operations that is used as an id.
    """
    ID_CONVERTER = Converters.string
    """
    The converter for the id.

    Note that converters do **cast** the value, so the converter 
    ``uuid`` will return an ``UUID`` object.
    """
    __type__ = None  # type: str
    """
    The type of resource. 
    If none, it is used the type of the Schema (``Schema.type``)
    """

    def __init__(
        self,
        app,
        import_name=__name__,
        static_folder=None,
        static_url_path=None,
        template_folder=None,
        url_prefix=None,
        subdomain=None,
        url_defaults=None,
        root_path=None,
        cli_commands: Iterable[Tuple[Callable, str or None]] = tuple(),
    ):
        assert not self.VIEW or issubclass(
            self.VIEW, View
        ), 'VIEW should be a subclass of View'
        assert not self.SCHEMA or issubclass(
            self.SCHEMA, Schema
        ), 'SCHEMA should be a subclass of Schema or None.'
        # todo test for cases where self.SCHEMA is None
        url_prefix = (
            url_prefix if url_prefix is not None else '/{}'.format(self.resource)
        )
        super().__init__(
            self.type,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
        )
        # todo __name__ in import_name forces subclasses to override the constructor
        #   otherwise import_name equals to teal.resource not project1.myresource
        #   and it is not very elegant...

        self.app = app
        self.schema = self.SCHEMA() if self.SCHEMA else None
        # Views
        if self.VIEW:
            view = self.VIEW.as_view('main', definition=self, auth=app.auth)
            if self.AUTH:
                view = app.auth.requires_auth(view)
            self.add_url_rule(
                '/', defaults={'id': None}, view_func=view, methods={'GET'}
            )
            self.add_url_rule('/', view_func=view, methods={'POST'})
            self.add_url_rule(
                '/<{}:{}>'.format(self.ID_CONVERTER.value, self.ID_NAME),
                view_func=view,
                methods={'GET', 'PUT', 'DELETE', 'PATCH'},
            )
        self.cli_commands = cli_commands
        self.before_request(self.load_resource)

    @classproperty
    def type(cls):
        t = cls.__type__ or cls.SCHEMA.t
        assert t, 'Resource needs a type: either from SCHEMA or manually from __type__.'
        return t

    @classproperty
    def t(cls):
        return cls.type

    @classproperty
    def resource(cls):
        return Naming.resource(cls.type)

    @classproperty
    def cli_name(cls):
        """The name used to generate the CLI Click group for this
        resource."""
        return inflection.singularize(cls.resource)

    def load_resource(self):
        """
        Loads a schema and resource_def into the current request so it
        can be used easily by functions outside view.
        """
        g.schema = self.schema
        g.resource_def = self

    def init_db(self, db: 'db.SQLAlchemy', exclude_schema=None):
        """
        Put here code to execute when initializing the database for this
        resource.

        We guarantee this to be executed in an app_context.

        No need to commit.
        """
        pass

    @property
    def subresources_types(self) -> Iterator[str]:
        """Gets the types of the subresources."""
        return (node.name for node in PreOrderIter(self.app.tree[self.t]))


TYPE = Union[
    Resource, Schema, 'db.Model', str, Type[Resource], Type[Schema], Type['db.Model']
]


def url_for_resource(resource: TYPE, item_id=None, method='GET') -> str:
    """
    As Flask's ``url_for``, this generates an URL but specifically for
    a View endpoint of the given resource.
    :param method: The method whose view URL should be generated.
    :param resource:
    :param item_id: If given, append the ID of the resource in the URL,
                    ex. GET /devices/1
    :return: An URL.
    """
    type = getattr(resource, 't', resource)
    values = {}
    if item_id:
        values[current_app.resources[type].ID_NAME] = item_id
    return url_for('{}.main'.format(type), _method=method, **values)
