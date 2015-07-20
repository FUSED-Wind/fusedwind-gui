
from flask import Flask, session
from flask_bootstrap import Bootstrap
from flask_appconfig import AppConfig
from flask.ext.bower import Bower

## Configuring the Flask app ---------------------------------------------------

app = Flask(__name__)
configfile=None
AppConfig(app, configfile)  # Flask-Appconfig is not necessary, but
                            # highly recommend =)
                            # https://github.com/mbr/flask-appconfig

Bootstrap(app)
Bower(app) # Usefull to use bower-components

# in a real app, these should be configured through Flask-Appconfig
app.config['SECRET_KEY'] = 'devkey'
