from flask import Flask, jsonify
from flask.views import MethodView

app = Flask(__name__)


@app.route('/')
def main():
    return "Welcome to Peterboy (Tomboy Sync Server)"


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
