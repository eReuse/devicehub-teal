import ipaddress
from distutils.version import StrictVersion
from typing import Type, Union

import colour
from boltons import strutils, urlutils
from ereuse_devicehub.ereuse_utils import if_none_return_none
from flask import current_app as app
from flask import g
from marshmallow import utils
from marshmallow.fields import Field
from marshmallow.fields import Nested as MarshmallowNested
from marshmallow.fields import String
from marshmallow.fields import ValidationError as _ValidationError
from marshmallow.fields import missing_
from marshmallow.validate import Validator
from marshmallow_enum import EnumField as _EnumField
from sqlalchemy_utils import PhoneNumber

from ereuse_devicehub.teal import db as tealdb
from ereuse_devicehub.teal.resource import Schema


class Version(Field):
    """A python StrictVersion field, like '1.0.1'."""

    @if_none_return_none
    def _serialize(self, value, attr, obj):
        return str(value)

    @if_none_return_none
    def _deserialize(self, value, attr, data):
        return StrictVersion(value)


class Color(Field):
    """Any color field that can be accepted by the colour package."""

    @if_none_return_none
    def _serialize(self, value, attr, obj):
        return str(value)

    @if_none_return_none
    def _deserialize(self, value, attr, data):
        return colour.Color(value)


class URL(Field):
    def __init__(
        self,
        require_path=False,
        default=missing_,
        attribute=None,
        data_key=None,
        error=None,
        validate=None,
        required=False,
        allow_none=None,
        load_only=False,
        dump_only=False,
        missing=missing_,
        error_messages=None,
        **metadata,
    ):
        super().__init__(
            default,
            attribute,
            data_key,
            error,
            validate,
            required,
            allow_none,
            load_only,
            dump_only,
            missing,
            error_messages,
            **metadata,
        )
        self.require_path = require_path

    @if_none_return_none
    def _serialize(self, value, attr, obj):
        return value.to_text()

    @if_none_return_none
    def _deserialize(self, value, attr, data):
        url = urlutils.URL(value)
        if url.scheme or url.host:
            if self.require_path:
                if url.path and url.path != '/':
                    return url
            else:
                return url
        raise ValueError('Not a valid URL.')


class IP(Field):
    @if_none_return_none
    def _serialize(
        self, value: Union[ipaddress.IPv4Address, ipaddress.IPv6Address], attr, obj
    ):
        return str(value)

    @if_none_return_none
    def _deserialize(self, value: str, attr, data):
        return ipaddress.ip_address(value)


class Phone(Field):
    @if_none_return_none
    def _serialize(self, value: PhoneNumber, attr, obj):
        return value.international

    @if_none_return_none
    def _deserialize(self, value: str, attr, data):
        phone = PhoneNumber(value)
        if not phone.is_valid_number():
            raise ValueError('The phone number is invalid.')
        return phone


class SanitizedStr(String):
    """String field that only has regular user strings.

    A String that removes whitespaces,
    optionally makes it lower, and invalidates HTML or ANSI codes.
    """

    def __init__(
        self,
        lower=False,
        default=missing_,
        attribute=None,
        data_key=None,
        error=None,
        validate=None,
        required=False,
        allow_none=None,
        load_only=False,
        dump_only=False,
        missing=missing_,
        error_messages=None,
        **metadata,
    ):
        super().__init__(
            default,
            attribute,
            data_key,
            error,
            validate,
            required,
            allow_none,
            load_only,
            dump_only,
            missing,
            error_messages,
            **metadata,
        )
        self.lower = lower

    def _deserialize(self, value, attr, data):
        out = super()._deserialize(value, attr, data)
        out = out.strip()
        if self.lower:
            out = out.lower()
        if strutils.html2text(out) != out:
            self.fail('invalid')
        elif strutils.strip_ansi(out) != out:
            self.fail('invalid')
        return out


class NestedOn(MarshmallowNested):
    """A relationship with a resource schema that emulates the
    relationships in SQLAlchemy.

    It allows instantiating SQLA models when deserializing NestedOn
    values in two fashions:

    - If the :attr:`.only_query` is set, NestedOn expects a scalar
      (str, int...) value when deserializing, and tries to get
      an existing model that has such value. Typical case is setting
      :attr:`.only_query` to ``id``, and then pass-in the id
      of a nested model. In such case NestedOn will change the id
      for the model representing the ID.
    - If :attr:`.only_query` is not set, NestedOn expects the
      value to deserialize to be a dictionary, and instantiates
      the model with the values of the dictionary. In this case
      NestedOn requires :attr:`.polymorphic_on` to be set as a field,
      usually called ``type``, that references a subclass of Model;
      ex. {'type': 'SpecificDevice', ...}.

    When serializing from :meth:`teal.resource.Schema.jsonify` it
    serializes nested relationships up to a defined limit.

    :param polymorphic_on: The field name that discriminates
                               the type of object. For example ``type``.
                               Then ``type`` contains the class name
                               of a subschema of ``nested``.
    """

    NESTED_LEVEL = '_level'
    NESTED_LEVEL_MAX = '_level_max'

    def __init__(
        self,
        nested,
        polymorphic_on: str,
        db: tealdb.SQLAlchemy,
        collection_class=list,
        default=missing_,
        exclude=tuple(),
        only_query: str = None,
        only=None,
        **kwargs,
    ):
        self.polymorphic_on = polymorphic_on
        self.collection_class = collection_class
        self.only_query = only_query
        assert isinstance(polymorphic_on, str)
        assert isinstance(only, str) or only is None
        super().__init__(nested, default, exclude, only, **kwargs)
        self.db = db

    def _deserialize(self, value, attr, data):
        if self.many and not utils.is_collection(value):
            self.fail('type', input=value, type=value.__class__.__name__)

        if isinstance(self.only, str):  # self.only is a field name
            if self.many:
                value = self.collection_class({self.only: v} for v in value)
            else:
                value = {self.only: value}
        # New code:
        parent_schema = app.resources[super().schema.t].SCHEMA
        if self.many:
            return self.collection_class(
                self._deserialize_one(single, parent_schema, attr) for single in value
            )
        else:
            return self._deserialize_one(value, parent_schema, attr)

    def _deserialize_one(self, value, parent_schema: Type[Schema], attr):
        if isinstance(value, dict) and self.polymorphic_on in value:
            type = value[self.polymorphic_on]
            resource = app.resources[type]
            if not issubclass(resource.SCHEMA, parent_schema):
                raise ValidationError(
                    '{} is not a sub-type of {}'.format(type, parent_schema.t),
                    field_names=[attr],
                )
            schema = resource.SCHEMA(
                only=self.only,
                exclude=self.exclude,
                context=getattr(self.parent, 'context', {}),
                load_only=self._nested_normalized_option('load_only'),
                dump_only=self._nested_normalized_option('dump_only'),
            )
            schema.ordered = getattr(self.parent, 'ordered', False)
            value = schema.load(value)
            model = self._model(type)(**value)
        elif self.only_query:  # todo test only_query
            model = (
                self._model(parent_schema.t)
                .query.filter_by(**{self.only_query: value})
                .one()
            )
        else:
            raise ValidationError(
                '\'Type\' field required to disambiguate resources.', field_names=[attr]
            )
        assert isinstance(model, tealdb.Model)
        return model

    def _model(self, type: str) -> Type[tealdb.Model]:
        """Given the type of a model it returns the model class."""
        return self.db.Model._decl_class_registry.data[type]()

    def serialize(self, attr: str, obj, accessor=None) -> dict:
        """See class docs."""
        if g.get(NestedOn.NESTED_LEVEL) == g.get(NestedOn.NESTED_LEVEL_MAX):
            # Idea from https://marshmallow-sqlalchemy.readthedocs.io
            # /en/latest/recipes.html#smart-nested-field
            # Gets the FK of the relationship instead of the full object
            # This won't work for many-many relationships (as they are lists)
            # In such case return None
            # todo is this the behaviour we want?
            return getattr(obj, attr + '_id', None)
        setattr(g, NestedOn.NESTED_LEVEL, g.get(NestedOn.NESTED_LEVEL) + 1)
        ret = super().serialize(attr, obj, accessor)
        setattr(g, NestedOn.NESTED_LEVEL, g.get(NestedOn.NESTED_LEVEL) - 1)
        return ret


class IsType(Validator):
    """
    Validator which succeeds if the value it is passed is a registered
    resource type.

    :param parent: If set, type must be a subtype of such resource.
                   By default accept any resource.
    """

    # todo remove if not needed
    no_type = 'Type does not exist.'
    no_subtype = 'Type is not a descendant type of {parent}'

    def __init__(self, parent: str = None) -> None:
        self.parent = parent  # type: str

    def _repr_args(self):
        return 'parent={0!r}'.format(self.parent)

    def __call__(self, type: str):
        assert not self.parent or self.parent in app.resources
        try:
            r = app.resources[type]
            if self.parent:
                if not issubclass(r.__class__, app.resources[self.parent].__class__):
                    raise ValidationError(self.no_subtype.format(self.parent))
        except KeyError:
            raise ValidationError(self.no_type)


class ValidationError(_ValidationError):
    code = 422


class EnumField(_EnumField):
    """
    An EnumField that allows
    generating OpenApi enums through Apispec.
    """

    def __init__(
        self,
        enum,
        by_value=False,
        load_by=None,
        dump_by=None,
        error='',
        *args,
        **kwargs,
    ):
        super().__init__(enum, by_value, load_by, dump_by, error, *args, **kwargs)
        self.metadata['enum'] = [e.name for e in enum]
