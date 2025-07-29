from flask import Flask
from ailice.app.log import logger


def CreateApp():
    app = Flask(__name__, static_folder='static')
    return app