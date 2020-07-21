Example stuff
=============

Example configurations useful for Devicehub.

You can use [App.py](./app.py), [Apache.conf](./apache.conf), 
and [wsgi.wsgi](./wsgi.wsgi) to configure Apache with Devicehub. Look
at each files to know what to configure.


Config with nginx and gunicorn
==============================
0.- dependencies of gunicorn in requirements.txt 
1.- install nginx with apt-get install nginx
2.- cp 01_api.dh.usody.net.conf /etc/nginx/sites-available/01_api.dh.usody.net.conf
3.- ln -sf /etc/nginx/sites-available/01_api.dh.usody.net.conf /etc/nginx/sites-enabled/
4.- cp gunicorn.service /etc/systemd/system/gunicorn.service
5.- mkdir /var/log/ereuse
6.- chown ereuse.ereuse /var/log/ereuse
7.- systemctl daemon-reload
8.- systemctl start gunicorn.service
9.- systemctl start nginx.service
