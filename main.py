import os

from flask import Flask
from flask_login import LoginManager
from socialmedia.views.auth import auth, load_user
from socialmedia.views.main import blueprint as main
from socialmedia.views.external_comms import blueprint as external_comms
from socialmedia.views.queue_workers import blueprint as queue_workers

try:
    import googleclouddebugger
    googleclouddebugger.enable(
        breakpoint_enable_canary=True
    )
except ImportError:
    pass

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

# need these for firebase login management
#import json
#from google.cloud import secretmanager
#from socialmedia.views.firebase import blueprint as firebase_views
#if os.environ.get('FIREBASE_AUTH_CONFIG'):
#    with open(os.environ['FIREBASE_AUTH_CONFIG']) as fb_auth_config_file:
#        firebase_auth_config = json.loads(fb_auth_config_file)
#else:
#    client = secretmanager.SecretManagerServiceClient()
#    name = f"projects/{os.environ.get('GOOGLE_CLOUD_PROJECT')}/secrets/firebase_auth_config/versions/1"
#    response = client.access_secret_version(request={"name": name})
#    firebase_auth_config = json.loads(response.payload.data.decode('UTF-8'))
#app.config['firebase_config'] = firebase_auth_config
#app.register_blueprint(firebase_views, url_prefix='/firebase')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
