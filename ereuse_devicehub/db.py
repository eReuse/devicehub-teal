from teal.db import SQLAlchemy as _SQLAlchemy


class SQLAlchemy(_SQLAlchemy):
    def drop_all(self, bind='__all__', app=None):
        """A faster nuke-like option to drop everything."""
        self.drop_schema()
        self.drop_schema(schema='common')


db = SQLAlchemy(session_options={"autoflush": False})
