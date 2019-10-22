import os

from flask import Flask, jsonify, request, render_template, url_for, redirect, \
    abort
from flask.views import MethodView

from flask_login import LoginManager, login_user
from oauthlib.oauth1 import OAuth1Error

from peterboy.api import UserAuthAPI, UserDetailAPI, UserNotesAPI, UserNoteAPI
from peterboy.database import db_session
from peterboy.lib import new_client, authorize_check, create_ref
from peterboy.models import User, PeterboyNote, PeterboySyncServer, PeterboySync
from peterboy.oauth_url import OAuthRequestToken, OAuthorize, IssueToken, init_oauth_url
from peterboy.user_auth import UserSignUp, UserSignIn

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = os.urandom(30)

login_manager = LoginManager(app)
login_manager.session_protection = "strong"
login_manager.login_view = "signin"

init_oauth_url(app)


@app.route('/')
def main():
    return render_template('web/index.html')


app.add_url_rule('/signup', view_func=UserSignUp.as_view('signup'))
app.add_url_rule('/signin', view_func=UserSignIn.as_view('signin'))

app.add_url_rule('/oauth/request_token', view_func=OAuthRequestToken.as_view('initiate_temporary_credential'))
app.add_url_rule('/oauth/authorize', view_func=OAuthorize.as_view('authorize'))
app.add_url_rule('/oauth/access_token', view_func=IssueToken.as_view('issue_token'))


@app.route("/<username>")
def user_space(username):
    # TODO 개발
    return "오시었나 당신아?"


@app.route("/<username>/notes")
def user_web_notes(username):
    # TODO 개발
    return "사용자 노트 목록"


@app.route("/<username>/notes/<note_id>")
def user_web_note(username, note_id):
    # TODO 개발
    return "사용자 노트 상세"


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
