from flask_sqlalchemy import SQLAlchemy

from teal.db import Model

db = SQLAlchemy(model_class=Model)
