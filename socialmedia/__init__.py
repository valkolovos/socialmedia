import os

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager

from socialmedia.views.auth import auth, load_user, request_loader
from socialmedia.views.main import blueprint as main
from socialmedia.views.external_comms import blueprint as external_comms
from socialmedia.views.queue_workers import blueprint as queue_workers
from socialmedia.views.update import blueprint as update

def create_app(
    model_datastore, stream_factory, url_signer, task_manager, get_shas,
    update_backend, update_frontend,
):
    app = Flask(__name__)
    # main handles all direct requests from the browser (html and json)
    app.register_blueprint(main)
    # auth handles authentication
    app.register_blueprint(auth)
    # external comms handles requests from other users' queue workers
    app.register_blueprint(external_comms, url_prefix='/api')
    # queue_workers handles queue messages
    app.register_blueprint(queue_workers, url_prefix='/worker')
    app.register_blueprint(update, url_prefix='/update')
    app.config.update(
        SECRET_KEY = os.environ.get('SECRET_KEY', 'e0c1dae0e44dd8239b8f01d83322d0cc')
    )

    # need these for flask login management
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    login_manager.user_loader(load_user)
    login_manager.request_loader(request_loader)

    # use datastore for data management
    app.datamodels = model_datastore

    app.stream_factory = stream_factory
    app.url_signer = url_signer
    app.task_manager = task_manager
    app.get_sha_function = get_shas
    app.update_backend_function = update_backend
    app.update_frontend_function = update_frontend

    CORS(app)
    return app
