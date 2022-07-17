import json

import requests

from flask import (
    current_app,
    Blueprint,
    request,
    session,
)
from flask_login import current_user

blueprint = Blueprint('update', __name__)

@blueprint.route('/')
def update_app():
    if current_user.is_authenticated:
        requesting_user = session.get('authenticated_user')
        if requesting_user or not requesting_user.get('admin'):
            return 'Not authorized', 401
    elif not request.headers.get('X-Appengine-Cron') == 'true':
        return 'Not authorized', 401

    try:
        current_shas = current_app.get_sha_function()
    except Exception as e:
        return e, 200
    latest_backend_sha = requests.get(
        'https://api.github.com/repos/valkolovos/socialmedia/commits?per_page=1'
    ).json()[0]['sha']
    latest_frontend_sha = requests.get(
        'https://api.github.com/repos/valkolovos/socialmedia-frontend/commits?per_page=1'
    ).json()[0]['sha']
    print(current_shas, latest_backend_sha, latest_frontend_sha)
    response = {
        'backend_update_triggered': False,
        'frontend_update_triggered': False,
    }
    if current_shas['serverSHA'] != latest_backend_sha:
        current_app.update_backend_function()
        response['backend_update_triggered'] = True
    if current_shas['frontendSHA'] != latest_frontend_sha:
        current_app.update_frontend_function()
        response['frontend_update_triggered'] = True
    return response, 200

