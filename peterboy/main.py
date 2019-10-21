import os
from functools import wraps
from uuid import uuid4

from flask import Flask, jsonify, request, render_template, url_for, redirect, \
    abort
from flask.views import MethodView
from authlib.flask.oauth1 import AuthorizationServer, current_credential
from authlib.flask.oauth1.sqla import create_query_client_func, \
    register_authorization_hooks
from oauthlib.oauth1 import OAuth1Error

from peterboy.database import db_session
from peterboy.models import Client, TimestampNonce, TemporaryCredential, \
    TokenCredential, User, PeterboyNote, PeterboySyncServer, PeterboySync

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

app = Flask(__name__)
app.url_map.strict_slashes = False
query_client = create_query_client_func(db_session, Client)
server = AuthorizationServer(app, query_client=query_client)
config_host = PeterboySyncServer.get_config('Host', '')

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
        print("POST 요청")
        # 여기에서 사용자를 생성한다.
        return ""


app.add_url_rule('/signup', view_func=UserSignUp.as_view('signup'))


@app.route('/signin')
def signin():
    return render_template('web/signin.html')


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


def authorization2dict(header):
    auth_header = header[1:].split(",")
    resp = {}

    for item in auth_header:
        first_equal = item.find("=")
        resp[item[:first_equal]] = item[first_equal + 1:][1:-1]

    return resp


@app.route("/<username>")
def user_space(username):
    return {}


@app.route("/favicon.ico")
def favicon_ico():
    return abort(404)


def authorize_check(error=True):
    def authorize_inner(f):
        @wraps(f)
        def check(*args, **kwargs):
            token_credential = None

            if 'Authorization' in request.headers:
                authorization = authorization2dict(request.headers['Authorization'])
                token_credential = TokenCredential.query.filter(
                    TokenCredential.oauth_token == authorization['oauth_token']).first()

            kwargs['token_user'] = token_credential.user if token_credential else None

            if error:
                abort(500)

            return f(*args, **kwargs)
        return check
    return authorize_inner


class UserAuthAPI(MethodView):
    decorators = [authorize_check(False)]

    def get(self, token_user=None):
        # 톰보이가 서버 연결 요청 버튼을 누르면 여기로 요청된다.
        # 여기에서 아이디를 받아 ID별로 사용자 구분(URL의 일부로 받을지 아니면 query param으로 받을건지 고민은 해봐야 함)
        # 단, URL의 일부로 받을 경우 /api/1.0은 개별 유저 공간에 포함되어야 하고 query param으로 받으면 그대로 루트 URL에 API가 속하게 됨

        resp = {
            "oauth_request_token_url": url_for('initiate_temporary_credential', _external=True),
            "oauth_authorize_url": url_for('authorize', _external=True),
            "oauth_access_token_url": url_for('issue_token', _external=True),
            "api-version": "1.0"
        }

        if token_user:
            resp.update({"user-ref": {
                "api-ref": url_for('user_detail', username=token_user.username, _external=True),
                "href": "{}/{}".format(config_host, token_user.username)
            }})

        return jsonify(resp)

    def post(self):
        print("POST 요청")
        return ""


app.add_url_rule('/api/1.0', view_func=UserAuthAPI.as_view('user_auth'))


class UserDetailAPI(MethodView):
    decorators = [authorize_check]

    def get(self, username, token_user=None):
        latest_sync_revision = PeterboySync.get_latest_revision(token_user.id)

        return jsonify({
            "user-name": username,
            "first-name": username,
            "last-name": username,
            "notes-ref": {
                "api-ref": url_for('user_notes', username=username, _external=True),
                "href": "{0}/{1}/notes".format(config_host, username)
            },
            "latest-sync-revision": latest_sync_revision,
            "current-sync-guid": token_user.current_sync_guid
        })


app.add_url_rule('/api/1.0/<username>', view_func=UserDetailAPI.as_view('user_detail'))


class UserNotesAPI(MethodView):
    decorators = [authorize_check]

    def get(self, username, token_user=None):
        latest_sync_revision = PeterboySync.get_latest_revision(token_user.id)

        since = request.args.get('since', 0, type=int)

        note_records = PeterboyNote.query
        if 'since' in request.args:
            note_records = note_records.filter(PeterboyNote.last_sync_revision > since)

        notes = []

        include_notes = request.args.get('include_notes', default=False, type=bool)

        for record in note_records:
            if include_notes:
                notes.append(record.toTomboy())
            else:
                notes.append(dict(
                    guid=record.guid,
                    title=record.title,
                    ref={
                        "api-ref": url_for('user_note', username=username, note_id=record.id, _external=True),
                        "href": "{}/{}/notes/{}".format(config_host, username, record.id)
                    }
                ))

        return jsonify({
            "latest-sync-revision": latest_sync_revision,
            "notes": notes
        })

    def put(self, username, token_user=None):
        note_changes = request.get_json()['note-changes']

        guid_list = map(lambda x: x['guid'], note_changes)
        exists_notes = PeterboyNote.query.filter(
            PeterboyNote.guid.in_(guid_list),
            PeterboyNote.user_id == token_user.id)
        db_updated_guid = [exist_note.guid for exist_note in exists_notes]

        latest_sync_revision = PeterboySync.get_latest_revision(token_user.id)

        new_sync_rev = latest_sync_revision + 1

        if 'latest-sync-revision' in request.get_json():
            new_sync_rev = request.get_json()['latest-sync-revision']

        if new_sync_rev != latest_sync_revision + 1:
            # TODO: Return a more useful error response?
            return abort(500)

        for exist_note in exists_notes:
            entry = filter(lambda x: x['guid'] == exist_note.guid, note_changes)
            entry = tuple(entry)[0]

            if ('command' in entry) and entry['command'] == 'delete':
                # TODO 2019/10/18일 톰보이 프로그램 버그로 보이는데 삭제되서 command가
                # 와야 하는데 안와서 일단 코드만 남겨둠.
                db_session.delete(exist_note)
                continue

            # 노트 버전이 동일하면 업데이트 하지 않는다
            if exist_note.note_content_version == entry['note-content-version']:
                continue

            exist_note.title = entry['title']
            exist_note.note_content = entry['note-content']
            exist_note.note_content_version = entry['note-content-version']
            exist_note.last_change_date = entry['last-change-date']
            exist_note.last_metadata_change_date = entry['last-metadata-change-date']
            exist_note.create_date = entry['create-date']
            exist_note.open_on_startup = entry['open-on-startup']
            exist_note.pinned = entry['pinned']
            exist_note.tags = entry['tags']
            exist_note.last_sync_revision = new_sync_rev

        for entry in note_changes:
            if entry['guid'] in db_updated_guid:
                continue

            note = PeterboyNote()
            note.guid = entry['guid']
            note.user_id = token_user.id
            note.title = entry['title']
            note.note_content = entry['note-content']
            note.note_content_version = entry['note-content-version']
            note.last_change_date = entry['last-change-date']
            note.last_metadata_change_date = entry['last-metadata-change-date']
            note.last_sync_revision = new_sync_rev
            note.create_date = entry['create-date']
            note.open_on_startup = entry['open-on-startup']
            note.pinned = entry['pinned']
            note.tags = entry['tags']

            db_session.add(note)

        # 마지막 싱크 리비전 저장
        latest_sync_revision = PeterboySync.commit_revision(token_user.id)

        db_session.commit()

        # 업데이트된 정보만 내려가도록 변경
        note_records = PeterboyNote.query
        notes = []

        for record in note_records:
            notes.append(dict(
                guid=record.guid,
                title=record.title,
                ref={
                    "api-ref": url_for('user_note', username=username, note_id=record.id, _external=True),
                    "href": "{}/{}/notes/{}".format(config_host, username, record.id)
                }
            ))

        return jsonify({
            "latest-sync-revision": latest_sync_revision,
            "notes": notes
        })


app.add_url_rule('/api/1.0/<username>/notes', view_func=UserNotesAPI.as_view('user_notes'))


class UserNoteAPI(MethodView):
    decorators = [authorize_check]

    def get(self, username, note_id, token_user=None):
        note = PeterboyNote.query.filter(
            PeterboyNote.user_id == token_user.id,
            PeterboyNote.id == note_id).first()

        return jsonify({"note": [note.toTomboy(
            hidden_last_sync_revision=True)]})


app.add_url_rule('/api/1.0/<username>/notes/<note_id>', view_func=UserNoteAPI.as_view('user_note'))
