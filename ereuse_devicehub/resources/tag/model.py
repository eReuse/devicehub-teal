from sqlalchemy import BigInteger, Column, ForeignKey, Unicode, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship, validates

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import Organization
from teal.db import DB_CASCADE_SET_NULL, URL
from teal.marshmallow import ValidationError


class Tag(Thing):
    id = Column(Unicode(), primary_key=True)
    org_id = Column(UUID(as_uuid=True),
                    ForeignKey(Organization.id),
                    primary_key=True,
                    # If we link with the Organization object this instance
                    # will be set as persistent and added to session
                    # which is something we don't want to enforce by default
                    default=lambda: Organization.get_default_org_id())
    org = relationship(Organization,
                       backref=backref('tags', lazy=True),
                       primaryjoin=Organization.id == org_id,
                       collection_class=set)
    provider = Column(URL(),
                      comment='The tag provider URL. If None, the provider is this Devicehub.')
    device_id = Column(BigInteger,
                       # We don't want to delete the tag on device deletion, only set to null
                       ForeignKey(Device.id, ondelete=DB_CASCADE_SET_NULL))
    device = relationship(Device,
                          backref=backref('tags', lazy=True, collection_class=set),
                          primaryjoin=Device.id == device_id)

    @validates('id')
    def does_not_contain_slash(self, _, value: str):
        if '/' in value:
            raise ValidationError('Tags cannot contain slashes (/).')
        return value

    __table_args__ = (
        UniqueConstraint(device_id, org_id, name='One tag per organization.'),
    )

    def __repr__(self) -> str:
        return '<Tag {0.id} org:{0.org_id} device:{0.device_id}>'.format(self)
