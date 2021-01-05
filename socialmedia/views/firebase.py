from flask import (
    Blueprint,
    render_template,
    request,
    session,
)
from socialmedia.dataclient import datastore_client
from socialmedia.views.auth_decorators import verify_user
from socialmedia.views.utils import create_profile as _create_profile


blueprint = Blueprint('firebase', __name__)

@blueprint.route('/sign-up')
def sign_up():
    return render_template('firebase_signup.html', context=context)

@blueprint.route('/create-profile', methods=['POST'])
@verify_user
def create_profile(user_id):
    _create_profile(user_id, request.form['display-name'], request.form['handle'])
    return '', 200

@blueprint.route('/check-user')
@verify_user
def check_user(user_id):
    if session.get('user', {'user_id': None})['user_id'] == user_id:
        return '', 200
    query = datastore_client.query(kind='Profile')
    query.add_filter('user_id', '=', user_id)
    profiles = list(query.fetch(limit=1))
    if not profiles:
        return 'Not Found', 404
    # removing private_key from user object in session
    profiles[0]['private_key'] = None
    # adding id to use for key creation later
    profiles[0]['id'] = profiles[0].id
    session['user'] = profiles[0]
    return '', 200

