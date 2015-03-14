__author__ = 'Excelle'

import logging; logging.basicConfig(level=logging.INFO)

import os
import time
from datetime import datetime

from core import db
from core.web import WSGIApplication, Jinja2TemplateEngine

from config.config import configs


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1 minute ago'
    if delta < 3600:
        return u'%s minutes ago' % (delta // 60)
    if delta < 86400:
        return u'%s hours ago' % (delta // 3600)
    if delta < 604800:
        return u'%s days ago' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s/%s/%s' % (dt.year, dt.month, dt.day)


# init db:
db.create_engine(**configs.db)

# init wsgi app:
wsgi = WSGIApplication(os.path.dirname(os.path.abspath(__file__)))

template_engine = Jinja2TemplateEngine(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
template_engine.add_filter('datetime', datetime_filter)

wsgi.template_engine = template_engine

import urls

wsgi.add_interceptor(urls.user_interceptor)
wsgi.add_interceptor(urls.admin_interceptor)
wsgi.add_module(urls)

if __name__ == '__main__':
    wsgi.run(port=9001, host='0.0.0.0')
else:
    application = wsgi.get_wsgi_application()
