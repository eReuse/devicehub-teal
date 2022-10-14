import logging

from flask import Blueprint

billing = Blueprint('billing', __name__, url_prefix='/billing')

logger = logging.getLogger(__name__)
