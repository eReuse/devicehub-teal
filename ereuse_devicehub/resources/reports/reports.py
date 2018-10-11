from typing import Set

from sqlalchemy import func

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.event.models import Price, Event, Trade

ids = {1,2,3}


def export(devices_id: Set[str]):
    # todo get the last event of device
    last_event = Event.end_time.

    devices = Device.id.in_(ids)

    total_value_query = db.session.query(Price, func.sum(Price.price).label('total'))\
        .filter(devices)\
        .join(Price.device)\
        .filter(last_event)

    # todo hacer query para obtener el price

    query(func.max(end_time)).join(Price.devices).filter(Device_id==id).ordey_by(Price.end_time).limit()

    total_price_query = query()

    value = total_value_query.one()
    value['total']

    #
    db.session.query(Price, (Price.price / total_value_query).label('asdfas'))

    trade_orgs_q = db.session.query(Trade, func.sum(Trade.org_id)).filter(devices).join(Trade.devices).filter(last_event)

    # execute query
    value = trade_orgs_q.scalar()

