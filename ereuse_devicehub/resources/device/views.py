from teal.resource import View


class DeviceView(View):

    def one(self, id):
        """Gets one device."""
        raise NotImplementedError
