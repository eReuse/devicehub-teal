from marshmallow import fields as ma_fields
from marshmallow import validate as ma_validate
from marshmallow.fields import Email

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.models import STR_SIZE, STR_SM_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.teal import enums
from ereuse_devicehub.teal.marshmallow import EnumField, Phone, SanitizedStr


class Agent(Thing):
    id = ma_fields.UUID(dump_only=True)
    name = SanitizedStr(validate=ma_validate.Length(max=STR_SM_SIZE))
    tax_id = SanitizedStr(
        lower=True, validate=ma_validate.Length(max=STR_SM_SIZE), data_key='taxId'
    )
    country = EnumField(enums.Country)
    telephone = Phone()
    email = Email()


class Organization(Agent):
    members = NestedOn('Membership')
    default_of = NestedOn('Inventory')


class Membership(Thing):
    organization = NestedOn(Organization)
    individual = NestedOn('Individual')
    id = SanitizedStr(lower=True, validate=ma_validate.Length(max=STR_SIZE))


class Individual(Agent):
    member_of = NestedOn(Membership, many=True)


class Person(Individual):
    pass


class System(Individual):
    pass
