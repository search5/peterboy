from flask import render_template, request, jsonify, url_for, redirect
from flask.views import MethodView
from flask_login import login_required, logout_user

from peterboy.models import User


class MyPage(MethodView):
    decorators = [login_required]

    def get(self):
        return render_template("web/mypage.html")

    def post(self):
        req_json = request.get_json()

        # ID 가져옴
        user = User.query.filter(
            User.username == req_json.get('user_id')).first()
        if not user:
            return jsonify(success=False, message='수정하려는 사용자가 없습니다')

        user.user_mail = req_json.get('user_email')
        user.name = req_json.get('user_name')

        # 새 비밀번호 여부
        if req_json.get('user_password') != "":
            user.userpw = req_json.get('user_password')

        return jsonify(success=True)


class Logout(MethodView):
    decorators = [login_required]

    def get(self):
        logout_user()
        return redirect(url_for('main'))
