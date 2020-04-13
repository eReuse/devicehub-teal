from flask import current_app as app
from marshmallow import Schema as MarshmallowSchema, ValidationError, fields as f, validates_schema
from marshmallow.fields import Boolean, DateTime, Integer, Nested, String, UUID
from marshmallow.validate import Length
from sqlalchemy.util import OrderedSet
from teal.marshmallow import SanitizedStr, URL
from teal.resource import Schema

from ereuse_devicehub.marshmallow import NestedOn
from ereuse_devicehub.resources.proof import models as m
from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE
from ereuse_devicehub.resources.schemas import Thing
from ereuse_devicehub.resources.action import schemas as s_action
from ereuse_devicehub.resources.device import schemas as s_device
from ereuse_devicehub.resources.user import schemas as s_user


class Proof(Thing):
    __doc__ = m.Proof.__doc__
    id = UUID(dump_only=True)
    ethereum_hash = SanitizedStr(default='', validate=Length(max=STR_BIG_SIZE),
                                   data_key="ethereumHash", required=True)
    url = URL(dump_only=True, description=m.Proof.url.__doc__)
    device_id = Integer(load_only=True, data_key='deviceID')
    device = NestedOn(s_device.Device, dump_only=True)


class ProofTransfer(Proof):
    __doc__ = m.ProofTransfer.__doc__
    deposit = Integer(validate=f.validate.Range(min=0, max=100))
    supplier_id = UUID(load_only=True, required=True, data_key='supplierID')
    receiver_id = UUID(load_only=True, required=True, data_key='receiverID')


class ProofDataWipe(Proof):
    __doc__ = m.ProofDataWipe.__doc__
    # erasure_type = String(default='', data_key='erasureType')
    date = DateTime('iso', required=True)
    result = Boolean(required=True)
    proof_author_id = SanitizedStr(validate=f.validate.Length(max=STR_SIZE),
                                   load_only=True, required=True, data_key='proofAuthorID')
    proof_author = NestedOn(s_user.User, dump_only=True)
    erasure = NestedOn(s_action.EraseBasic, only_query='id', data_key='erasureID')


class ProofFunction(Proof):
    __doc__ = m.ProofFunction.__doc__
    disk_usage = Integer(validate=f.validate.Range(min=0, max=100), data_key='diskUsage')
    proof_author_id = SanitizedStr(validate=f.validate.Length(max=STR_SIZE),
                                   load_only=True, required=True, data_key='proofAuthorID')
    proof_author = NestedOn(s_user.User, dump_only=True)
    rate = NestedOn(s_action.Rate, required=True,
                    only_query='id', data_key='rateID')


class ProofReuse(Proof):
    __doc__ = m.ProofReuse.__doc__
    receiver_segment = String(default='', data_key='receiverSegment', required=True)
    id_receipt = String(default='', data_key='idReceipt', required=True)
    supplier_id = UUID(load_only=True, required=False, data_key='supplierID')
    receiver_id = UUID(load_only=True, required=False, data_key='receiverID')
    price = Integer(required=True)


class ProofRecycling(Proof):
    __doc__ = m.ProofRecycling.__doc__
    collection_point = SanitizedStr(default='', data_key='collectionPoint', required=True)
    date = DateTime('iso', required=True)
    contact = SanitizedStr(default='', required=True)
    ticket = SanitizedStr(default='', required=True)
    gps_location = SanitizedStr(default='', data_key='gpsLocation', required=True)
    recycler_code = SanitizedStr(default='', data_key='recyclerCode', required=True)
