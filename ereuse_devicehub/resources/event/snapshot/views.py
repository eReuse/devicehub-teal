from teal.resource import View


class SnapshotView(View):
    def post(self):
        """Creates a Snapshot."""
        return super().post()

    def delete(self, id):
        """Deletes a Snapshot"""
        return super().delete(id)

    def patch(self, id):
        """Modifies a Snapshot"""
        return super().patch(id)


