from ereuse_devicehub.resources.device.models import Device
from teal.resource import View


class DeviceView(View):

    def get(self, id):
        """
        Devices view
        ---
        description: Gets a device or multiple devices.
        parameters:
          - name: id
            type: integer
            in: path
            description: The identifier of the device.
        responses:
          200:
            description: The device or devices.
        """
        return super().get(id)

    def one(self, id: int):
        """Gets one device."""
        device = Device.query.filter_by(id=id).one()
        return self.schema.jsonify(device)

    def find(self, args: dict):
        """Gets many devices."""
        devices = Device.query.all()
        return self.schema.jsonify(devices, many=True)
