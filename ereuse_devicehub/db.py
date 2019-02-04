import citext
from sqlalchemy import event
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import expression
from sqlalchemy_utils import view
from teal.db import SchemaSQLAlchemy


class SQLAlchemy(SchemaSQLAlchemy):
    """
    Superuser must create the required extensions in the public
    schema of the database, as it is in the `search_path`
    defined in teal.
    """
    # todo add here all types of columns used so we don't have to
    #   manually import them all the time
    UUID = postgresql.UUID
    CIText = citext.CIText

    def drop_all(self, bind='__all__', app=None, common_schema=True):
        """A faster nuke-like option to drop everything."""
        self.drop_schema()
        if common_schema:
            self.drop_schema(schema='common')


def create_view(name, selectable):
    """Creates a view.

    This is an adaptation from sqlalchemy_utils.view. See
     `the test on sqlalchemy-utils <https://github.com/kvesteri/
    sqlalchemy-utils/blob/master/tests/test_views.py>`_ for an
    example on how to use.
    """
    table = view.create_table_from_selectable(name, selectable)

    # We need to ensure views are created / destroyed before / after
    # SchemaSQLAlchemy's listeners execute
    # That is why insert=True in 'after_create'
    event.listen(db.metadata, 'after_create', view.CreateView(name, selectable), insert=True)
    event.listen(db.metadata, 'before_drop', view.DropView(name))
    return table


db = SQLAlchemy(session_options={'autoflush': False})
f = db.func
exp = expression
