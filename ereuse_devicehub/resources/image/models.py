from uuid import uuid4

from sqlalchemy import BigInteger, Column, Enum as DBEnum, ForeignKey, Unicode
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship
from sqlalchemy.util import OrderedSet

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.enums import ImageMimeTypes, Orientation
from ereuse_devicehub.resources.models import STR_BIG_SIZE, Thing
from teal.db import CASCADE_OWN


class ImageList(Thing):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id = Column(BigInteger, ForeignKey(Device.id), nullable=False)
    device = relationship(Device,
                          primaryjoin=Device.id == device_id,
                          backref=backref('images',
                                          lazy=True,
                                          cascade=CASCADE_OWN,
                                          order_by=lambda: ImageList.created,
                                          collection_class=OrderedSet))


class Image(Thing):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Unicode(STR_BIG_SIZE), default='', nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    file_format = db.Column(DBEnum(ImageMimeTypes), nullable=False)
    orientation = db.Column(DBEnum(Orientation), nullable=False)
    image_list_id = Column(UUID(as_uuid=True), ForeignKey(ImageList.id), nullable=False)
    image_list = relationship(ImageList,
                              primaryjoin=ImageList.id == image_list_id,
                              backref=backref('images',
                                              cascade=CASCADE_OWN,
                                              order_by=lambda: Image.created,
                                              collection_class=OrderedSet))

    # todo make an image Field that converts to/from image object
    # todo which metadata we get from Photobox?
