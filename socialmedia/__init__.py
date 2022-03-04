import os

from flask import Flask
from flask_login import LoginManager

from socialmedia.views.auth import auth, load_user
from socialmedia.views.main import blueprint as main
from socialmedia.views.external_comms import blueprint as external_comms
from socialmedia.views.queue_workers import blueprint as queue_workers

def create_app(model_datastore, stream_factory, url_signer, task_manager):
    app = Flask(__name__)
    # main handles all direct requests from the browser (html and json)
    app.register_blueprint(main)
    # auth handles authentication
    app.register_blueprint(auth)
    # external comms handles requests from other users' queue workers
    app.register_blueprint(external_comms, url_prefix='/api')
    # queue_workers handles queue messages
    app.register_blueprint(queue_workers, url_prefix='/worker')
    app.config.update(
        SECRET_KEY = os.environ.get('SECRET_KEY', 'e0c1dae0e44dd8239b8f01d83322d0cc')
    )

    # need these for flask login management
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    login_manager.user_loader(load_user)

    # use datastore for data management
    app.datamodels = model_datastore

    app.stream_factory = stream_factory
    app.url_signer = url_signer
    app.task_manager = task_manager

    return app

