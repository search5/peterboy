import os
from uuid import uuid4

from flask import Flask, jsonify, request, render_template, url_for, redirect
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
config_host = PeterboySyncServer.get_config('Host')

register_authorization_hooks(
    server, db_session,
    token_credential_model=TokenCredential,
    temporary_credential_model=TemporaryCredential,
    timestamp_nonce_model=TimestampNonce,
)


@app.route('/')
def main():
    return render_template('web/index.html')


@app.route('/signup')
def signup():
    return render_template('web/signup.html')


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
        resp[item[:first_equal]] = item[first_equal+1:][1:-1]

    return resp


@app.route("/<username>")
def user_space(username):
    return {}


class UserAuthAPI(MethodView):
    def get(self):
        # 톰보이가 서버 연결 요청 버튼을 누르면 여기로 요청된다.
        # 여기에서 아이디를 받아 ID별로 사용자 구분(URL의 일부로 받을지 아니면 query param으로 받을건지 고민은 해봐야 함)
        # 단, URL의 일부로 받을 경우 /api/1.0은 개별 유저 공간에 포함되어야 하고 query param으로 받으면 그대로 루트 URL에 API가 속하게 됨

        resp = {
            "oauth_request_token_url": "{}/oauth/request_token".format(config_host),
            "oauth_authorize_url": "{}/oauth/authorize".format(config_host),
            "oauth_access_token_url": "{}/oauth/access_token".format(config_host),
            "api-version": "1.0"
        }

        if 'Authorization' in request.headers:
            authorization = authorization2dict(request.headers['Authorization'])
            token_credential = TokenCredential.query.filter(TokenCredential.oauth_token == authorization['oauth_token']).first()
            if not token_credential:
                return {}

            resp.update({"user-ref": {
                "api-ref": "{}/api/1.0/{}".format(config_host, token_credential.user.username),
                "href": "{}/{}".format(config_host, token_credential.user.username)
            }})

        return jsonify(resp)

    def post(self):
        print("POST 요청")


app.add_url_rule('/api/1.0', view_func=UserAuthAPI.as_view('user_auth'))

class UserDetailAPI(MethodView):
    def get(self, user_id):
        if 'Authorization' in request.headers:
            authorization = authorization2dict(request.headers['Authorization'])
            token_credential = TokenCredential.query.filter(TokenCredential.oauth_token == authorization['oauth_token']).first()
            if not token_credential:
                return {}

            latest_sync_revision = -1
            sync_stat = PeterboySync.query.filter(PeterboySync.user_id == user_id).first()
            if sync_stat:
                latest_sync_revision = sync_stat.latest_sync_revision

            return jsonify({
                "user-name": user_id,
                "first-name":user_id,
                "last-name": user_id,
                "notes-ref": {
                    "api-ref": "{}/api/1.0/{0}/notes".format(config_host, token_credential.user.username),
                    "href": "{}/{0}/notes".format(config_host, token_credential.user.username)
                },
                "latest-sync-revision": latest_sync_revision,
                "current-sync-guid": "ff2e91b2-1234-4eab-3000-abcde49a7705"
            })


app.add_url_rule('/api/1.0/<user_id>', view_func=UserDetailAPI.as_view('user_detail'))

class UserNotesAPI(MethodView):
    def get(self, user_id):
        if 'Authorization' in request.headers:
            authorization = authorization2dict(request.headers['Authorization'])
            token_credential = TokenCredential.query.filter(TokenCredential.oauth_token == authorization['oauth_token']).first()
            if not token_credential:
                return {}

        note_records = PeterboyNote.query
        notes = []

        include_notes = request.args.get('include_notes', 'false')
        user_record = User.query.filter(User.id == user_id).first()

        for record in note_records:
            if include_notes == 'true':
                notes.append(record.toTomboy())
            else:
                notes.append(dict(
                    guid=record.guid,
                    title=record.title,
                    ref={
                        "api-ref": "{}/api/1.0/{}/notes/{}".format(config_host, user_record.username, record.id),
                        "href": "{}/{}/notes/{}".format(config_host, user_record.username, record.id)
                    }
                ))

        latest_sync_revision = -1
        sync_stat = PeterboySync.query.filter(PeterboySync.user_id == user_id).first()
        if sync_stat:
            latest_sync_revision = sync_stat.latest_sync_revision

        return jsonify({
            "latest-sync-revision": latest_sync_revision,
            "notes": notes
        })

    def put(self, user_id):
        if 'Authorization' in request.headers:
            authorization = authorization2dict(request.headers['Authorization'])
            token_credential = TokenCredential.query.filter(TokenCredential.oauth_token == authorization['oauth_token']).first()
            if not token_credential:
                return {}

        note_changes = request.get_json()['note-changes']

        for entry in note_changes:
            note = PeterboyNote()
            note.guid = entry['guid']
            note.user_id = user_id
            note.title = entry['title']
            note.note_content = entry['note-content']
            note.note_content_version = entry['note-content-version']
            note.last_change_date = entry['last-change-date']
            note.last_metadata_change_date = entry['last-metadata-change-date']
            note.create_date = entry['create-date']
            note.open_on_startup = entry['open-on-startup']
            note.pinned = entry['pinned']
            note.tags = entry['tags']

            db_session.add(note)

        # 싱크 리비전 저장
        sync_stat = PeterboySync.query.filter(PeterboySync.user_id == user_id).first()
        if not sync_stat:
            sync_stat = PeterboySync()
            sync_stat.user_id = user_id
            db_session.add(sync_stat)

        sync_stat.latest_sync_revision += 1
        sync_stat.current_sync_guid = str(uuid4())

        db_session.commit()

        return jsonify({
            "latest-sync-revision": sync_stat.latest_sync_revision,
            "notes": note_changes
        })

app.add_url_rule('/api/1.0/<user_id>/notes', view_func=UserNotesAPI.as_view('user_notes'))

# http://domain/api/1.0/user/notes/id
"""
{
    "note": [{
        "guid": "002e91a2-2e34-4e2d-bf88-21def49a7705",
        "title": "New Note 6",
        "note-content": "Describe your note <b>here</b>.",
        "note-content-version": 0.1,
        "last-change-date": "2009-04-19T21:29:23.2197340-07:00",
        "last-metadata-change-date": "2009-04-19T21:29:23.2197340-07:00",
        "create-date": "2008-03-06T13:44:46.4342680-08:00",
        "open-on-startup": false,
        "pinned": false,
        "tags": ["tag1", "tag2", "tag3", "system:notebook:biology"]
    }]
}
"""