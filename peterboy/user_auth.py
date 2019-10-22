from flask import render_template, request, jsonify, url_for, redirect, abort
from flask.views import MethodView
from flask_login import login_user

from peterboy.database import db_session
from peterboy.lib import new_client
from peterboy.models import User


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
