from sqlalchemy import BigInteger, Column, Sequence
from sqlalchemy_utils import EmailType

from ereuse_devicehub.resources.model import Thing


class User(Thing):
    id = Column(BigInteger, Sequence('user_seq'), primary_key=True)
    email = Column(EmailType, nullable=False)
