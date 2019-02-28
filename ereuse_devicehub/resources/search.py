"""Full text search module.

Implements full text search by using Postgre's capabilities and
creating temporary tables containing keywords as ts_vectors.
"""
from enum import Enum
from typing import Tuple

from ereuse_devicehub.db import db


class Weight(Enum):
    """TS Rank weight as an Enum."""
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'


class Search:
    """Methods for building queries with Postgre's Full text search.

    Based on `Rachid Belaid's post <http://rachbelaid.com/
    postgres-full-text-search-is-good-enough/>`_ and
    `Code for America's post <https://www.codeforamerica.org/blog/2015/07/02/
    multi-table-full-text-search-with-postgres-flask-and-sqlalchemy/>`.
    """
    LANG = 'english'

    @staticmethod
    def match(column: db.Column, search: str, lang=LANG):
        """Query that matches a TSVECTOR column with search words."""
        return column.op('@@')(db.func.websearch_to_tsquery(lang, search))

    @staticmethod
    def rank(column: db.Column, search: str, lang=LANG):
        """Query that ranks a TSVECTOR column with search words."""
        return db.func.ts_rank(column, db.func.websearch_to_tsquery(lang, search))

    @staticmethod
    def _vectorize(col: db.Column, weight: Weight = Weight.D, lang=LANG):
        return db.func.setweight(db.func.to_tsvector(lang, db.func.coalesce(col, '')), weight.name)

    @classmethod
    def vectorize(cls, *cols_with_weights: Tuple[db.Column, Weight], lang=LANG):
        """Produces a query that takes one ore more columns and their
        respective weights, and generates one big TSVECTOR.

        This method takes care of `null` column values.
        """
        first, rest = cols_with_weights[0], cols_with_weights[1:]
        tokens = cls._vectorize(*first, lang=lang)
        for unit in rest:
            tokens = tokens.concat(cls._vectorize(*unit, lang=lang))
        return tokens
