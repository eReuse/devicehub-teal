from contextlib import suppress
from typing import Set

from boltons import urlutils
from flask import g
from sqlalchemy import BigInteger, Column, ForeignKey, Sequence, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship, validates

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.agent.models import Organization
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.models import Thing
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.resources.utils import hashcode
from ereuse_devicehub.teal.db import DB_CASCADE_SET_NULL, URL, Query
from ereuse_devicehub.teal.marshmallow import ValidationError
from ereuse_devicehub.teal.resource import url_for_resource


class Tags(Set['Tag']):
    def __str__(self) -> str:
        return ', '.join(str(tag) for tag in self).strip()

    def __format__(self, format_spec):
        return ', '.join(format(tag, format_spec) for tag in self).strip()


class Tag(Thing):
    internal_id = Column(
        BigInteger, Sequence('tag_internal_id_seq'), unique=True, nullable=False
    )
    internal_id.comment = """The identifier of the tag for this database. Used only
    internally for software; users should not use this.
    """
    id = Column(db.CIText(), primary_key=True)
    id.comment = """The ID of the tag."""
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey(User.id),
        primary_key=True,
        nullable=False,
        default=lambda: g.user.id,
    )
    owner = relationship(User, primaryjoin=owner_id == User.id)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey(Organization.id),
        # If we link with the Organization object this instance
        # will be set as persistent and added to session
        # which is something we don't want to enforce by default
        default=lambda: Organization.get_default_org_id(),
    )
    org = relationship(
        Organization,
        backref=backref('tags', lazy=True),
        primaryjoin=Organization.id == org_id,
        collection_class=set,
    )
    """The organization that issued the tag."""
    provider = Column(URL())
    provider.comment = """The tag provider URL. If None, the provider is
    this Devicehub.
    """
    device_id = Column(
        BigInteger,
        # We don't want to delete the tag on device deletion, only set to null
        ForeignKey(Device.id, ondelete=DB_CASCADE_SET_NULL),
    )
    device = relationship(
        Device,
        backref=backref('tags', lazy=True, collection_class=Tags),
        primaryjoin=Device.id == device_id,
    )
    """The device linked to this tag."""
    secondary = Column(db.CIText(), index=True)
    secondary.comment = """A secondary identifier for this tag.
    It has the same constraints as the main one. Only needed in special cases.
    """

    __table_args__ = (db.Index('device_id_index', device_id, postgresql_using='hash'),)

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
            raise ValidationError(
                'Provider can only contain scheme and host', field_names=['provider']
            )
        return url

    __table_args__ = (
        UniqueConstraint(id, owner_id, name='one tag id per owner'),
        UniqueConstraint(
            secondary, owner_id, name='one secondary tag per organization'
        ),
    )

    @property
    def type(self) -> str:
        return self.__class__.__name__

    @property
    def url(self) -> urlutils.URL:
        """The URL where to GET this device."""
        # todo this url only works for printable internal tags
        return urlutils.URL(url_for_resource(Tag, item_id=self.code))

    @property
    def printable(self) -> bool:
        """Can the tag be printed by the user?

        Only tags that are from the default organization can be
        printed by the user.
        """
        return self.org_id == Organization.get_default_org_id()

    @classmethod
    def is_printable_q(cls):
        """Return a SQLAlchemy filter expression for printable queries."""
        return cls.org_id == Organization.get_default_org_id()

    @property
    def code(self) -> str:
        return hashcode.encode(self.internal_id)

    @property
    def get_provider(self) -> str:
        return self.provider.to_text() if self.provider else ''

    def delete(self):
        """Deletes the tag.

        This method removes the tag if is named tag and don't have any linked device.
        """
        if self.device:
            raise TagLinked(self)
        if self.provider:
            # if is an unnamed tag not delete
            raise TagUnnamed(self.id)

        db.session.delete(self)

    def __repr__(self) -> str:
        return '<Tag {0.id} org:{0.org_id} device:{0.device_id}>'.format(self)

    def __str__(self) -> str:
        return '{0.id} org: {0.org.name} device: {0.device}'.format(self)

    def __format__(self, format_spec: str) -> str:
        return '{0.org.name} {0.id}'.format(self)


class TagLinked(ValidationError):
    def __init__(self, tag):
        message = 'The tag {} is linked to device {}.'.format(tag.id, tag.device.id)
        super().__init__(message, field_names=['device'])


class TagUnnamed(ValidationError):
    def __init__(self, id):
        message = 'This tag {} is unnamed tag. It is imposible delete.'.format(id)
        super().__init__(message, field_names=['device'])
