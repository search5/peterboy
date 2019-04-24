import os

from flask import Flask, jsonify, request, render_template
from flask.views import MethodView
from authlib.flask.oauth1 import AuthorizationServer
from authlib.flask.oauth1.sqla import create_query_client_func, \
    register_authorization_hooks
from oauthlib.oauth1 import OAuth1Error
from sqlalchemy.sql.functions import current_user

from peterboy.database import db_session
from peterboy.models import Client, TimestampNonce, TemporaryCredential, \
    TokenCredential, User

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

app = Flask(__name__)
query_client = create_query_client_func(db_session, Client)

# server = AuthorizationServer()
server = AuthorizationServer(app, query_client=query_client)
# server.init_app(app, query_client=query_client)

from authlib.flask.oauth1.sqla import (
    register_nonce_hooks,
    register_temporary_credential_hooks,
    register_token_credential_hooks
)

register_authorization_hooks(
    server, db_session,
    token_credential_model=TokenCredential,
    temporary_credential_model=TemporaryCredential,
    timestamp_nonce_model=TimestampNonce,
)

# def token_generator():
#     return {
#         'oauth_token': random_string(20),
#         'oauth_token_secret': random_string(46)
#     }


@app.route('/')
def main():
    return "Welcome to Peterboy (Tomboy Sync Server)"


@app.route('/oauth/request_token', methods=['GET', 'POST'])
def initiate_temporary_credential():
    req_form = {'oauth_consumer_key': 'client',
            'oauth_callback': 'oob',
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': 'secret&'}
    return server.create_temporary_credentials_response()


@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    # make sure that user is logged in for yourself
    if request.method == 'GET':
        try:
            req = server.check_authorization_request()
            print(dir(req))
            return render_template('authorize.html', req=req)
            # return 'ok'
        except OAuth1Error as error:
            return render_template('error.html', error=error)

    granted = request.form.get('granted')
    if granted:
        grant_user = User.query.get(int(granted))
    else:
        grant_user = None

    try:
        return server.create_authorization_response(request, grant_user)
    except OAuth1Error as error:
        return render_template('error.html', error=error)


@app.route('/oauth/token', methods=['POST'])
def issue_token():
    return server.create_token_response()


class UserAuthAPI(MethodView):
    def get(self):
        # 톰보이가 서버 연결 요청 버튼을 누르면 여기로 요청된다.

        return jsonify({
            "oauth_request_token_url": "http://127.0.0.1:5002/oauth/request_token",
            "oauth_authorize_url": "http://127.0.0.1:5002/oauth/authorize",
            "oauth_access_token_url": "http://127.0.0.1:5002/oauth/access_token",
            "api-version": "1.0"
        })

    def post(self):
        print("POST 요청")


app.add_url_rule('/api/1.0', view_func=UserAuthAPI.as_view('user_auth'))
