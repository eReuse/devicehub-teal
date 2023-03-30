from typing import Dict, List

from flask import Response, jsonify, request
from webargs.flaskparser import FlaskParser

from ereuse_devicehub.teal.query import NestedQueryFlaskParser


class SearchQueryParser(NestedQueryFlaskParser):
    def parse_querystring(self, req, name, field):
        if name == 'search':
            v = FlaskParser.parse_querystring(self, req, name, field)
        else:
            v = super().parse_querystring(req, name, field)
        return v


def things_response(
    items: List[Dict],
    page: int = None,
    per_page: int = None,
    total: int = None,
    previous: int = None,
    next: int = None,
    url: str = None,
    code: int = 200,
) -> Response:
    """Generates a Devicehub API list conformant response for multiple
    things.
    """
    response = jsonify(
        {
            'items': items,
            # todo pagination should be in Header like github
            # https://developer.github.com/v3/guides/traversing-with-pagination/
            'pagination': {
                'page': page,
                'perPage': per_page,
                'total': total,
                'previous': previous,
                'next': next,
            },
            'url': url or request.path,
        }
    )
    response.status_code = code
    return response
