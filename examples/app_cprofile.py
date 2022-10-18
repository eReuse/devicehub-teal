from werkzeug.middleware.profiler import ProfilerMiddleware

from ereuse_devicehub.devicehub import Devicehub

app = Devicehub(inventory='dbtest')
app.config["SQLALCHEMY_RECORD_QUERIES"] = True
app.config['PROFILE'] = True
app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
app.run(debug=True)
