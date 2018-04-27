from ereuse_devicehub.resources.device.models import Device
from teal.resource import View


class DeviceView(View):
    def one(self, id: int):
        """Gets one device."""
        return Device.query.filter_by(id=id).one()
