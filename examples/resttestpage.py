from eve.utils import config, debug_error_message, validate_filters

from flask import abort
from eve_peewee import EvePeewee, BaseModel

import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    from eve import Eve
    from flask import Flask, request, send_from_directory
    import os
    cwd = os.path.dirname(os.path.abspath(__file__))
    app = Eve(data=EvePeewee)

    @app.route('/', defaults={'path': 'index.html'})
    @app.route('/<path:path>')
    def send_js(path):
        return send_from_directory(cwd + '/static', path)

    logger.info("registered paths: %s", app.url_map)
    app.run()

