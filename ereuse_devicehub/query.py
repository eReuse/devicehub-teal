from teal.query import NestedQueryFlaskParser
from webargs.flaskparser import FlaskParser


class SearchQueryParser(NestedQueryFlaskParser):

    def parse_querystring(self, req, name, field):
        if name == 'search':
            v = FlaskParser.parse_querystring(self, req, name, field)
        else:
            v = super().parse_querystring(req, name, field)
        return v
