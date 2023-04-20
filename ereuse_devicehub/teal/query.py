import json
from json import JSONDecodeError

from ereuse_devicehub.ereuse_utils import flatten_mixed
from marshmallow import Schema as MarshmallowSchema
from marshmallow.fields import Boolean, Field, List, Nested, Str, missing_
from sqlalchemy import Column, between, or_
from webargs.flaskparser import FlaskParser


class ListQuery(List):
    """Base class for list-based queries."""

    def __init__(self, column: Column, cls_or_instance, **kwargs):
        self.column = column
        super().__init__(cls_or_instance, **kwargs)


class Between(ListQuery):
    """
    Generates a `Between` SQL statement.

    This method wants the user to provide exactly two parameters:
    min and max::

        f = Between(Model.foo, Integer())
        ...
        Query().loads({'f': [0, 100]}

    """

    def _deserialize(self, value, attr, data):
        l = super()._deserialize(value, attr, data)
        return between(self.column, *l)


class Equal(Field):
    """
    Generates an SQL equal ``==`` clause for a given column and value::

        class MyArgs(Query):
            f = Equal(MyModel.foo, Integer())
        MyArgs().load({'f': 24}) -> SQL: ``MyModel.foo == 24``

    """

    def __init__(
        self,
        column: Column,
        field: Field,
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
        self.column = column
        self.field = field

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.column == self.field.deserialize(v)


class Or(List):
    """
    Generates an `OR` SQL statement. This is like a Marshmallow List field,
    so you can specify the type of value of the OR and validations.

    As an example, you can define with this a list of options::

        f = Or(Equal(Model.foo, Str(validates=OneOf(['option1', 'option2'])))

    Where the user can select one or more::

        {'f': ['option1']}

    And with ``Length`` you can enforce the user to only choose one option::

        f = Or(..., validates=Length(equal=1))
    """

    def _deserialize(self, value, attr, data):
        l = super()._deserialize(value, attr, data)
        return or_(v for v in l)


class ILike(Str):
    """
    Generates a insensitive `LIKE` statement for strings.
    """

    def __init__(
        self,
        column: Column,
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
        self.column = column

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.column.ilike('{}%'.format(v))


class QueryField(Field):
    """A field whose first parameter is a function that when
    executed by passing only the value returns a SQLAlchemy query
    expression.
    """

    def __init__(
        self,
        query,
        field: Field,
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
        self.query = query
        self.field = field

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.query(v)


class Join(Nested):
    # todo Joins are manual: they should be able to use ORM's join
    def __init__(
        self, join, nested, default=missing_, exclude=tuple(), only=None, **kwargs
    ):
        super().__init__(nested, default, exclude, only, **kwargs)
        self.join = join

    def _deserialize(self, value, attr, data):
        v = list(super()._deserialize(value, attr, data))
        v.append(self.join)
        return v


class Query(MarshmallowSchema):
    """
    A Marshmallow schema that outputs SQLAlchemy queries when ``loading``
    dictionaries::

        class MyQuery(Query):
            foo = Like(Mymodel.foocolumn)

        Mymodel.query.filter(*MyQuery().load({'foo': 'bar'})).all()
        # Executes query SELECT ... WHERE foocolumn IS LIKE 'bar%'

    When used with ``webargs`` library you can pass generate queries
    directly from the browser: ``foo.com/foo/?filter={'foo': 'bar'}``.
    """

    def load(self, data, many=None, partial=None):
        """
        Flatten ``Nested`` ``Query`` and add the list of results to
        a SQL ``AND``.
        """
        values = super().load(data, many, partial).values()
        return flatten_mixed(values)

    def dump(self, obj, many=None, update_fields=True):
        raise NotImplementedError('Why would you want to dump a query?')


class Sort(MarshmallowSchema):
    """
    A Marshmallow schema that outputs SQLAlchemy order clauses::

        class MySort(Sort):
            foo = SortField(MyModel.foocolumn)
        MyModel.query.filter(...).order_by(*MyQuery().load({'foo': 0})).all()

    When used with ``webargs`` library you can pass generate sorts
    directly from the browser: ``foo.com/foo/?sort={'foo': 1, 'bar': 0}``.
    """

    ASCENDING = True
    """Sort in ascending order."""
    DESCENDING = False
    """Sort in descending order."""

    def load(self, data, many=None, partial=None):
        values = super().load(data, many, partial).values()
        return flatten_mixed(values)


class SortField(Boolean):
    """A field that outputs a SQLAlchemy order clause."""

    def __init__(
        self, column: Column, truthy=Boolean.truthy, falsy=Boolean.falsy, **kwargs
    ):
        super().__init__(truthy, falsy, **kwargs)
        self.column = column

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.column.asc() if v else self.column.desc()


class NestedQueryFlaskParser(FlaskParser):
    """
    Parses JSON-encoded URL parameters like
    ``.../foo?param={"x": "y"}&param2=["x", "y"]``, and it still allows
    normal non-JSON-encoded params ``../foo?param=23&param2={"a": "b"}``.

    You can keep a value always a string, regardless if it is a valid
    JSON, by overriding the following method and setting per-case
    actions by checking `name` property.
    """

    def parse_querystring(self, req, name, field):
        v = super().parse_querystring(req, name, field)
        try:
            return json.loads(v)
        except (JSONDecodeError, TypeError):
            return v


class FullTextSearch(Str):
    # todo this is dummy for now
    pass
