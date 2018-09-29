from contextlib import suppress

from sqlalchemy import BigInteger, Column, ForeignKey, Unicode, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship, validates
from teal.db import DB_CASCADE_SET_NULL, Query, URL
from teal.marshmallow import ValidationError

from ereuse_devicehub.resources.agent.models import Organization
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing


class Tag(Thing):
    id = Column(Unicode(), primary_key=True)
    id.comment = """The ID of the tag."""
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
    """The organization that issued the tag."""
    provider = Column(URL())
    provider.comment = """
        The tag provider URL. If None, the provider is this Devicehub.
    """
    device_id = Column(BigInteger,
                       # We don't want to delete the tag on device deletion, only set to null
                       ForeignKey(Device.id, ondelete=DB_CASCADE_SET_NULL))
    device = relationship(Device,
                          backref=backref('tags', lazy=True, collection_class=set),
                          primaryjoin=Device.id == device_id)
    """The device linked to this tag."""
    secondary = Column(Unicode())
    secondary.comment = """
        A secondary identifier for this tag. It has the same
        constraints as the main one. Only needed in special cases.
    """

    def __init__(self, id: str, **kwargs) -> None:
        super().__init__(id=id, **kwargs)

    def like_etag(self):
        """Checks if the tag conforms to the `eTag spec <http:
        //devicehub.ereuse.org/tags.html#etags>`_.
        """
        with suppress(ValueError):
            provider, id = self.id.split('-')
            if len(provider) == 2 and 5 <= len(id) <= 10:
                return True
        return False

    @classmethod
    def from_an_id(cls, id: str) -> Query:
        """Query to look for a tag from a possible identifier."""
        return cls.query.filter((cls.id == id) | (cls.secondary == id))

    @validates('id', 'secondary')
    def does_not_contain_slash(self, _, value: str):
        if '/' in value:
            raise ValidationError('Tags cannot contain slashes (/).')
        return value

    @validates('provider')
    def use_only_domain(self, _, url: URL):
        if url.path:
            raise ValidationError('Provider can only contain scheme and host',
                                  field_names=['provider'])
        return url

    __table_args__ = (
        UniqueConstraint(device_id, org_id, name='one_tag_per_org'),
        UniqueConstraint(secondary, org_id, name='one_secondary_per_org')
    )

    def __repr__(self) -> str:
        return '<Tag {0.id} org:{0.org_id} device:{0.device_id}>'.format(self)
