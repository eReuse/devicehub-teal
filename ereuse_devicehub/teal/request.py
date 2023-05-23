from flask import Request as _Request
from flask import current_app as app

from ereuse_devicehub.teal.resource import Schema


class Request(_Request):
    def get_json(
        self,
        force=False,
        silent=False,
        cache=True,
        validate=True,
        schema: Schema = None,
    ) -> dict:
        """
        As :meth:`flask.Request.get_json` but parsing
        the resulting json through passed-in ``schema`` (or by default
        ``g.schema``).
        """
        json = super().get_json(force, silent, cache)
        if validate:
            json = (
                schema.load(json)
                if schema
                else app.resources[self.blueprint].schema.load(json)
            )
        return json
