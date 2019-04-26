import os

from flask import Flask, jsonify, request, render_template, url_for, redirect
from flask.views import MethodView
from authlib.flask.oauth1 import AuthorizationServer, current_credential
from authlib.flask.oauth1.sqla import create_query_client_func, \
    register_authorization_hooks
from oauthlib.oauth1 import OAuth1Error

from peterboy.database import db_session
from peterboy.models import Client, TimestampNonce, TemporaryCredential, \
    TokenCredential, User

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

app = Flask(__name__)
app.url_map.strict_slashes = False
query_client = create_query_client_func(db_session, Client)

# server = AuthorizationServer()
server = AuthorizationServer(app, query_client=query_client)
# server.init_app(app, query_client=query_client)


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
    return render_template('web/signup.html')\


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
def user_space():
    return {}


class UserAuthAPI(MethodView):
    def get(self):
        # 톰보이가 서버 연결 요청 버튼을 누르면 여기로 요청된다.
        # 여기에서 아이디를 받아 ID별로 사용자 구분(URL의 일부로 받을지 아니면 query param으로 받을건지 고민은 해봐야 함)
        # 단, URL의 일부로 받을 경우 /api/1.0은 개별 유저 공간에 포함되어야 하고 query param으로 받으면 그대로 루트 URL에 API가 속하게 됨

        resp = {
            "oauth_request_token_url": "http://127.0.0.1:5002/oauth/request_token",
            "oauth_authorize_url": "http://127.0.0.1:5002/oauth/authorize",
            "oauth_access_token_url": "http://127.0.0.1:5002/oauth/access_token",
            "api-version": "1.0"
        }

        if 'Authorization' in request.headers:
            authorization = authorization2dict(request.headers['Authorization'])
            token_credential = TokenCredential.query.filter(TokenCredential.oauth_token == authorization['oauth_token']).first()
            if not token_credential:
                return {}

            resp.update({"user-ref": {
                "api-ref": "http://127.0.0.1:5002/api/1.0/{}".format(token_credential.user.username),
                "href": "http://127.0.0.1:5002/{}".format(token_credential.user.username)
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

        return jsonify({
            "user-name": user_id,
            "first-name":user_id,
            "last-name": user_id,
            "notes-ref": {
                "api-ref": "http://127.0.0.1:5002/api/1.0/{0}/notes".format(token_credential.user.username),
                "href": "http://127.0.0.1:5002/{0}/notes".format(token_credential.user.username)
            },
            "latest-sync-revision": -1,
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
        """
        {
            "guid": "002e91a2-2e34-4e2d-bf88-21def49a7705",
            "title": "New Note 6",
            "note-content": "Describe your note <b>here</b>.",
            "note-content-version": 0.1,
            "last-change-date": "2009-04-19T21:29:23.2197340-07:00",
            "last-metadata-change-date": "2009-04-19T21:29:23.2197340-07:00",
            "create-date": "2008-03-06T13:44:46.4342680-08:00",
            "last-sync-revision": 57,
            "open-on-startup": False,
            "pinned": False,
            "tags": ["tag1", "tag2", "tag3", "system:notebook:biology"]
        }
        """
        return jsonify({
            "latest-sync-revision": -1,
            "notes": []
        })

    def put(self, user_id):
        if 'Authorization' in request.headers:
            authorization = authorization2dict(request.headers['Authorization'])
            token_credential = TokenCredential.query.filter(TokenCredential.oauth_token == authorization['oauth_token']).first()
            if not token_credential:
                return {}

        print(request.get_json())
        """
        {
            'note-changes': [
                {
                    'guid': 'e346f347-9ad6-4068-8d2e-5c08a49c4da1',
                    'title': '새 쪽지 5',
                    'note-content': '새 쪽지를 적으십시오.',
                    'note-content-version': 0.1,
                    'last-change-date': '2019-04-24T19:07:26.7452790+09:00',
                    'last-metadata-change-date': '2019-04-24T19:07:26.7452790+09:00',
                    'create-date': '2019-04-24T19:07:26.7452790+09:00',
                    'open-on-startup': False,
                    'pinned': False,
                    'tags': []
                }
            ],
            'latest-sync-revision': 0
        }
        """

        return jsonify({
            "latest-sync-revision": -1,
            "notes": []
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