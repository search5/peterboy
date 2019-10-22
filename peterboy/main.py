import os
from functools import wraps
from uuid import uuid4

from flask import Flask, jsonify, request, render_template, url_for, redirect, \
    abort
from flask.views import MethodView
from authlib.flask.oauth1 import AuthorizationServer, current_credential
from authlib.flask.oauth1.sqla import create_query_client_func, \
    register_authorization_hooks
from flask_login import LoginManager, login_user
from oauthlib.oauth1 import OAuth1Error

from peterboy.api import UserAuthAPI, UserDetailAPI, UserNotesAPI, UserNoteAPI
from peterboy.database import db_session
from peterboy.lib import new_client, authorize_check, create_ref
from peterboy.models import Client, TimestampNonce, TemporaryCredential, \
    TokenCredential, User, PeterboyNote, PeterboySyncServer, PeterboySync

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

query_client = create_query_client_func(db_session, Client)


app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = os.urandom(30)
server = AuthorizationServer(app, query_client=query_client)
login_manager = LoginManager(app)
login_manager.session_protection = "strong"
login_manager.login_view = "signin"

register_authorization_hooks(
    server, db_session,
    token_credential_model=TokenCredential,
    temporary_credential_model=TemporaryCredential,
    timestamp_nonce_model=TimestampNonce,
)


@app.route('/')
def main():
    return render_template('web/index.html')


class UserSignUp(MethodView):
    def get(self):
        return render_template('web/signup.html')

    def post(self):
        req_json = request.get_json()

        # ID 중복 검사
        user = User.query.filter(
            User.username == req_json.get('user_id')).first()
        if user:
            return jsonify(success=False, message='가입하시려는 아이디가 있습니다')

        user = User(username=req_json.get('user_id'),
                    user_mail=req_json.get('user_email'),
                    name=req_json.get('user_name'),
                    userpw=req_json.get('user_password'))
        db_session.add(user)
        db_session.flush()

        client = new_client(user.id)
        db_session.add(client)

        login_user(user, remember=True)

        return jsonify(success=True)


app.add_url_rule('/signup', view_func=UserSignUp.as_view('signup'))


class UserSignIn(MethodView):
    def get(self):
        return render_template('web/signin.html')

    def post(self):
        user = User.query.filter(
            User.username == request.form.get('user_id')).first()

        if user and user.userpw == request.form.get('user_password'):
            login_user(user, remember=True)
            return redirect(url_for('user_space', username='jiho'))
        else:
            # TODO: 로그인 실패 페이지로 돌려보내야 함
            # 사용자가 없거나 비밀번호가 일치하지 않습니다
            # 비밀번호는 sha256 등으로 해시 키 구해야 함
            return redirect(abort(500))


app.add_url_rule('/signin', view_func=UserSignIn.as_view('signin'))


@app.route('/oauth/request_token', methods=['GET', 'POST'])
def initiate_temporary_credential():
    return server.create_temporary_credentials_response()


@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    # make sure that user is logged in for yourself
    if request.method == 'GET':
        try:
            req = server.check_authorization_request()
            return render_template('oauth/authorize.html', req=req)
        except OAuth1Error as error:
            return render_template('oauth/error.html', error=error)

    granted = request.form.get('granted')
    if granted:
        grant_user = User.query.get(int(granted))
        grant_user.current_sync_guid = str(uuid4())
    else:
        grant_user = None

    try:
        return server.create_authorization_response(request, grant_user)
    except OAuth1Error as error:
        return render_template('oauth/error.html', error=error)


@app.route('/oauth/access_token', methods=['POST'])
def issue_token():
    return server.create_token_response()


@app.route("/<username>")
def user_space(username):
    return "오시었나 당신아?"


@app.route("/favicon.ico")
def favicon_ico():
    return abort(404)


app.add_url_rule('/api/1.0', view_func=UserAuthAPI.as_view('user_auth'))
app.add_url_rule('/api/1.0/<username>', view_func=UserDetailAPI.as_view('user_detail'))
app.add_url_rule('/api/1.0/<username>/notes', view_func=UserNotesAPI.as_view('user_notes'))
app.add_url_rule('/api/1.0/<username>/notes/<note_id>', view_func=UserNoteAPI.as_view('user_note'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter(User.username == user_id).first()


@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception is None:
        db_session.commit()
    else:
        db_session.rollback()

    db_session.remove()



