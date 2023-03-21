import datetime
from functools import wraps

from flask import Response, make_response


def cache(expires: datetime.timedelta = None):
    """Sets HTTP cache for now + passed-in time.

    Example usage::

        @app.route('/map')
        @header_cache(expires=datetime.datetime(seconds=50))
        def index():
          return render_template('index.html')
    """

    def cache_decorator(view):
        @wraps(view)
        def cache_func(*args, **kwargs):
            r = make_response(view(*args, **kwargs))  # type: Response
            r.expires = datetime.datetime.now(datetime.timezone.utc) + expires
            r.cache_control.public = True
            return r

        return cache_func

    return cache_decorator
