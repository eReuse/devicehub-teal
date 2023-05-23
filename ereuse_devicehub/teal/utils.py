import inspect
from typing import Dict, Iterator, Tuple

from sqlalchemy.dialects import postgresql

from ereuse_devicehub.teal import resource


def compiled(Model, query) -> Tuple[str, Dict[str, str]]:
    """
    Generates a SQL statement.

    :return A tuple with 1. the SQL statement and 2. the params for it.
    """
    c = Model.query.filter(*query).statement.compile(dialect=postgresql.dialect())
    return str(c), c.params


def import_resource(module) -> Iterator['resource.Resource']:
    """
    Gets the resource classes from the passed-in module.

    This method yields subclasses of :class:`teal.resource.Resource`
    found in the given module.
    """

    for obj in vars(module).values():
        if (
            inspect.isclass(obj)
            and issubclass(obj, resource.Resource)
            and obj != resource.Resource
        ):
            yield obj
