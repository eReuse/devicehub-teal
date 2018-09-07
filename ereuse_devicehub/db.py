from sqlalchemy.dialects import postgresql
from teal.db import SchemaSQLAlchemy


class SQLAlchemy(SchemaSQLAlchemy):
    """
    Superuser must create the required extensions in the public
    schema of the database, as it is in the `search_path`
    defined in teal.
    """
    UUID = postgresql.UUID

    def drop_all(self, bind='__all__', app=None):
        """A faster nuke-like option to drop everything."""
        self.drop_schema()
        self.drop_schema(schema='common')


db = SQLAlchemy(session_options={"autoflush": False})
