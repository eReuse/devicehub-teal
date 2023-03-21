import enum
import ipaddress
import re
import uuid
from distutils.version import StrictVersion
from typing import Any, Type, Union

from boltons.typeutils import classproperty
from boltons.urlutils import URL as BoltonsUrl
from ereuse_devicehub.ereuse_utils import if_none_return_none
from flask_sqlalchemy import BaseQuery
from flask_sqlalchemy import Model as _Model
from flask_sqlalchemy import SignallingSession
from flask_sqlalchemy import SQLAlchemy as FlaskSQLAlchemy
from sqlalchemy import CheckConstraint, SmallInteger, cast, event, types
from sqlalchemy.dialects.postgresql import ARRAY, INET
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy_utils import Ltree
from werkzeug.exceptions import BadRequest, NotFound, UnprocessableEntity


class ResourceNotFound(NotFound):
    # todo show id
    def __init__(self, resource: str) -> None:
        super().__init__('The {} doesn\'t exist.'.format(resource))


class MultipleResourcesFound(UnprocessableEntity):
    # todo show id
    def __init__(self, resource: str) -> None:
        super().__init__(
            'Expected only one {} but multiple where found'.format(resource)
        )


POLYMORPHIC_ID = 'polymorphic_identity'
POLYMORPHIC_ON = 'polymorphic_on'
INHERIT_COND = 'inherit_condition'
DEFAULT_CASCADE = 'save-update, merge'
CASCADE_DEL = '{}, delete'.format(DEFAULT_CASCADE)
CASCADE_OWN = '{}, delete-orphan'.format(CASCADE_DEL)
DB_CASCADE_SET_NULL = 'SET NULL'


class Query(BaseQuery):
    def one(self):
        try:
            return super().one()
        except NoResultFound:
            raise ResourceNotFound(self._entities[0]._label_name)
        except MultipleResultsFound:
            raise MultipleResourcesFound(self._entities[0]._label_name)


class Model(_Model):
    # Just provide typing
    query_class = Query  # type: Type[Query]
    query = None  # type: Query

    @classproperty
    def t(cls):
        return cls.__name__


class Session(SignallingSession):
    """A SQLAlchemy session that raises better exceptions."""

    def _flush(self, objects=None):
        try:
            super()._flush(objects)
        except IntegrityError as e:
            raise DBError(e)  # This creates a suitable subclass


class SchemaSession(Session):
    """Session that is configured to use a PostgreSQL's Schema.

    Idea from `here <https://stackoverflow.com/a/9299021>`_.
    """

    def __init__(self, db, autocommit=False, autoflush=True, **options):
        super().__init__(db, autocommit, autoflush, **options)
        self.execute('SET search_path TO {}, public'.format(self.app.schema))


class StrictVersionType(types.TypeDecorator):
    """StrictVersion support for SQLAlchemy as Unicode.

    Idea `from official documentation <http://docs.sqlalchemy.org/en/
    latest/core/custom_types.html#augmenting-existing-types>`_.
    """

    impl = types.Unicode

    @if_none_return_none
    def process_bind_param(self, value, dialect):
        return str(value)

    @if_none_return_none
    def process_result_value(self, value, dialect):
        return StrictVersion(value)


class URL(types.TypeDecorator):
    """bolton's URL support for SQLAlchemy as Unicode."""

    impl = types.Unicode

    @if_none_return_none
    def process_bind_param(self, value: BoltonsUrl, dialect):
        return value.to_text()

    @if_none_return_none
    def process_result_value(self, value, dialect):
        return BoltonsUrl(value)


class IP(types.TypeDecorator):
    """ipaddress support for SQLAlchemy as PSQL INET."""

    impl = INET

    @if_none_return_none
    def process_bind_param(self, value, dialect):
        return str(value)

    @if_none_return_none
    def process_result_value(self, value, dialect):
        return ipaddress.ip_address(value)


class IntEnum(types.TypeDecorator):
    """SmallInteger -- IntEnum"""

    impl = SmallInteger

    def __init__(self, enumeration: Type[enum.IntEnum], *args, **kwargs):
        self.enum = enumeration
        super().__init__(*args, **kwargs)

    @if_none_return_none
    def process_bind_param(self, value, dialect):
        assert isinstance(value, self.enum), 'Value should be instance of {}'.format(
            self.enum
        )
        return value.value

    @if_none_return_none
    def process_result_value(self, value, dialect):
        return self.enum(value)


class UUIDLtree(Ltree):
    """This Ltree only wants UUIDs as paths elements."""

    def __init__(self, path_or_ltree: Union[Ltree, uuid.UUID]):
        """
        Creates a new Ltree. If the passed-in value is an UUID,
        it automatically generates a suitable string for Ltree.
        """
        if not isinstance(path_or_ltree, Ltree):
            if isinstance(path_or_ltree, uuid.UUID):
                path_or_ltree = self.convert(path_or_ltree)
            else:
                raise ValueError(
                    'Ltree does not accept {}'.format(path_or_ltree.__class__)
                )
        super().__init__(path_or_ltree)

    @staticmethod
    def convert(id: uuid.UUID) -> str:
        """Transforms an uuid to a ready-to-ltree str representation."""
        return str(id).replace('-', '_')


def check_range(column: str, min=1, max=None) -> CheckConstraint:
    """Database constraint for ranged values."""
    constraint = (
        '>= {}'.format(min) if max is None else 'BETWEEN {} AND {}'.format(min, max)
    )
    return CheckConstraint('{} {}'.format(column, constraint))


def check_lower(field_name: str):
    """Constraint that checks if the string is lower case."""
    return CheckConstraint(
        '{0} = lower({0})'.format(field_name),
        name='{} must be lower'.format(field_name),
    )


class ArrayOfEnum(ARRAY):
    """
    Allows to use Arrays of Enums for psql.

    From `the docs <http://docs.sqlalchemy.org/en/latest/dialects/
    postgresql.html?highlight=array#postgresql-array-of-enum>`_
    and `this issue <https://bitbucket.org/zzzeek/sqlalchemy/issues/
    3467/array-of-enums-does-not-allow-assigning>`_.
    """

    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)

    def result_processor(self, dialect, coltype):
        super_rp = super(ArrayOfEnum, self).result_processor(dialect, coltype)

        def handle_raw_string(value):
            inner = re.match(r'^{(.*)}$', value).group(1)
            return inner.split(',') if inner else []

        def process(value):
            if value is None:
                return None
            return super_rp(handle_raw_string(value))

        return process


class SQLAlchemy(FlaskSQLAlchemy):
    """
    Enhances :class:`flask_sqlalchemy.SQLAlchemy` by adding our
    Session and Model.
    """

    StrictVersionType = StrictVersionType
    URL = URL
    IP = IP
    IntEnum = IntEnum
    UUIDLtree = UUIDLtree
    ArrayOfEnum = ArrayOfEnum

    def __init__(
        self,
        app=None,
        use_native_unicode=True,
        session_options=None,
        metadata=None,
        query_class=BaseQuery,
        model_class=Model,
    ):
        super().__init__(
            app, use_native_unicode, session_options, metadata, query_class, model_class
        )

    def create_session(self, options):
        """As parent's create_session but adding our Session."""
        return sessionmaker(class_=Session, db=self, **options)


class SchemaSQLAlchemy(SQLAlchemy):
    """
    Enhances :class:`flask_sqlalchemy.SQLAlchemy` by using PostgreSQL's
    schemas when creating/dropping tables.

    See :attr:`teal.config.SCHEMA` for more info.
    """

    def __init__(
        self,
        app=None,
        use_native_unicode=True,
        session_options=None,
        metadata=None,
        query_class=Query,
        model_class=Model,
    ):
        super().__init__(
            app, use_native_unicode, session_options, metadata, query_class, model_class
        )
        # The following listeners set psql's search_path to the correct
        # schema and create the schemas accordingly

        # Specifically:
        # 1. Creates the schemas and set ``search_path`` to app's config SCHEMA
        event.listen(self.metadata, 'before_create', self.create_schemas)
        # Set ``search_path`` to default (``public``)
        event.listen(self.metadata, 'after_create', self.revert_connection)
        # Set ``search_path`` to app's config SCHEMA
        event.listen(self.metadata, 'before_drop', self.set_search_path)
        # Set ``search_path`` to default (``public``)
        event.listen(self.metadata, 'after_drop', self.revert_connection)

    def create_all(self, bind='__all__', app=None, exclude_schema=None):
        """Create all tables.

        :param exclude_schema: Do not create tables in this schema.
        """
        app = self.get_app(app)
        # todo how to pass exclude_schema without contaminating self?
        self._exclude_schema = exclude_schema
        super().create_all(bind, app)

    def _execute_for_all_tables(self, app, bind, operation, skip_tables=False):
        # todo how to pass app to our event listeners without contaminating self?
        self._app = self.get_app(app)
        super()._execute_for_all_tables(app, bind, operation, skip_tables)

    def get_tables_for_bind(self, bind=None):
        """As super method, but only getting tales that are not
        part of exclude_schema, if set.
        """
        tables = super().get_tables_for_bind(bind)
        if getattr(self, '_exclude_schema', None):
            tables = [t for t in tables if t.schema != self._exclude_schema]
        return tables

    def create_schemas(self, target, connection, **kw):
        """
        Create the schemas and set the active schema.

        From `here <https://bitbucket.org/zzzeek/sqlalchemy/issues/3914/
        extend-create_all-drop_all-to-include#comment-40129850>`_.
        """
        schemas = set(table.schema for table in target.tables.values() if table.schema)
        if self._app.schema:
            schemas.add(self._app.schema)
        for schema in schemas:
            connection.execute('CREATE SCHEMA IF NOT EXISTS {}'.format(schema))
        self.set_search_path(target, connection)

    def set_search_path(self, _, connection, **kw):
        app = self.get_app()
        if app.schema:
            connection.execute('SET search_path TO {}, public'.format(app.schema))

    def revert_connection(self, _, connection, **kw):
        connection.execute('SET search_path TO public')

    def create_session(self, options):
        """As parent's create_session but adding our SchemaSession."""
        return sessionmaker(class_=SchemaSession, db=self, **options)

    def drop_schema(self, app=None, schema=None):
        """Nukes a schema and everything that depends on it."""
        app = self.get_app(app)
        schema = schema or app.schema
        with self.engine.begin() as conn:
            conn.execute('DROP SCHEMA IF EXISTS {} CASCADE'.format(schema))

    def has_schema(self, schema: str) -> bool:
        """Does the db have the passed-in schema?"""
        return self.engine.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname='{}')".format(
                schema
            )
        ).scalar()


class DBError(BadRequest):
    """An Error from the database.

    This helper error is used to map SQLAlchemy's IntegrityError
    to more precise errors (like UniqueViolation) that are understood
    as a client-ready HTTP Error.

    When instantiating the class it auto-selects the best error.
    """

    def __init__(self, origin: IntegrityError):
        super().__init__(str(origin))
        self._origin = origin

    def __new__(cls, origin: IntegrityError) -> Any:
        msg = str(origin)
        if 'unique constraint' in msg.lower():
            return super().__new__(UniqueViolation)
        return super().__new__(cls)


class UniqueViolation(DBError):
    def __init__(self, origin: IntegrityError):
        super().__init__(origin)
        self.constraint = self.description.split('"')[1]
        self.field_name = None
        self.field_value = None
        if isinstance(origin.params, dict):
            self.field_name, self.field_value = next(
                (k, v) for k, v in origin.params.items() if k in self.constraint
            )
