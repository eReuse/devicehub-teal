from teal.db import SQLAlchemy

db = SQLAlchemy(session_options={"autoflush": False})
