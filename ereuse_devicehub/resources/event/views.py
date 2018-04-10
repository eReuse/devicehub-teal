from teal.resource import View


class EventView(View):
    def one(self, id):
        """Gets one event."""
        return super().one(id)
