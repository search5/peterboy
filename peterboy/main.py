import io
import os
import xml

import paginate
from dateutil.parser import parse
from flask import Flask, jsonify, request, render_template, url_for, redirect, \
    abort
from flask.views import MethodView

from flask_login import LoginManager, login_required, current_user, logout_user
from markupsafe import Markup
from paginate_sqlalchemy import SqlalchemyOrmWrapper
from sqlalchemy import desc

from peterboy.api import UserAuthAPI, UserDetailAPI, UserNotesAPI, UserNoteAPI
from peterboy.database import db_session
from peterboy.lib import paginate_link_tag, TomboyXMLHandler, notebook_names
from peterboy.models import User, PeterboyNote, PeterboySync, PeterboyNotebook
from peterboy.oauth_url import OAuthRequestToken, OAuthorize, IssueToken, init_oauth_url
from peterboy.user_auth import UserSignUp, UserSignIn
from peterboy.user_info import MyPage, Logout

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = os.urandom(30)

login_manager = LoginManager(app)
login_manager.session_protection = "strong"
login_manager.login_view = "signin"

init_oauth_url(app)

app.add_url_rule('/signup', view_func=UserSignUp.as_view('signup'))
app.add_url_rule('/signin', view_func=UserSignIn.as_view('signin'))

app.add_url_rule('/oauth/request_token',
                 view_func=OAuthRequestToken.as_view('request_token'))
app.add_url_rule('/oauth/authorize', view_func=OAuthorize.as_view('authorize'))
app.add_url_rule('/oauth/access_token',
                 view_func=IssueToken.as_view('access_token'))


@app.route('/')
def main():
    if current_user.is_anonymous:
        return render_template('web/index.html')
    else:
        return redirect(url_for('user_space', username=current_user.username))


@app.route("/<username>")
@login_required
def user_space(username):
    # 등록된 노트 수
    note_cnt = PeterboyNote.query.join(User).filter(User.username == username)

    # 마지막 싱크 리비전
    user_record = User.query.filter(User.username == username).first()
    latest_sync_revision = PeterboySync.get_latest_revision(user_record.id)

    return render_template("web/user_space/main.html",
                           note_cnt=note_cnt.count(),
                           latest_sync_revision=latest_sync_revision)


@app.route("/<username>/notes")
@login_required
def user_web_notes(username):
    current_page = request.args.get("page", 1, type=int)

    notebook = request.args.get('notebook', '')
    search_word = request.args.get("search_word", '')

    # if search_option and search_option in ['classify', 'subject']:
    #     search_column = getattr(FAQ, search_option)

    page_param = {}

    if notebook:
        page_param["notebook"] = notebook

    if search_word:
        page_param["search_word"] = search_word

    page_url = url_for("user_web_notes", username=username, **page_param)

    if len(page_param.keys()) > 0:
        page_url = str(page_url) + "&page=$page"
    else:
        page_url = str(page_url) + "?page=$page"

    items_per_page = 10

    notebooks = notebook_names(notebook)

    notes = PeterboyNote.query.join(User).outerjoin(PeterboyNotebook).filter(User.username == username)
    if notebook:
        notes = notes.filter(PeterboyNotebook.note_id.in_(notebooks))
    # if search_word:
    #     records = records.filter(
    #         search_column.ilike('%{}%'.format(search_word)))
    notes = notes.order_by(desc(PeterboyNote.id))
    total_cnt = notes.count()

    paginator = paginate.Page(notes, current_page, page_url=page_url,
                              items_per_page=items_per_page,
                              wrapper_class=SqlalchemyOrmWrapper)

    return render_template("web/user_space/notes.html", paginator=paginator,
                           paginate_link_tag=paginate_link_tag,
                           page_url=page_url, items_per_page=items_per_page,
                           total_cnt=total_cnt, page=current_page)


@app.route("/<username>/notes/<note_id>")
@login_required
def user_web_note(username, note_id):
    note = PeterboyNote.query.join(User).filter(
        User.username == username, PeterboyNote.id == note_id).first()

    return render_template("web/user_space/note_view.html", note=note)


@app.route("/<username>/notes/<note_id>/edit")
@login_required
def user_web_note_edit(username, note_id):
    note = PeterboyNote.query.join(User).filter(
        User.username == username, PeterboyNote.id == note_id).first()

    return render_template("web/user_space/note_edit.html", note=note)


@app.route("/<username>/notes/<note_id>/edit", methods=["POST"])
@login_required
def user_web_note_edit_save(username, note_id):
    note = PeterboyNote.query.join(User).filter(
        User.username == username, PeterboyNote.id == note_id).first()

    # 노트 내용을 Tomboy 형식으로 변환할 필요 있음(TODO)
    note.note_content = request.get_json()['note_content']

    return jsonify(success=True)


@app.route("/<username>/notes/<note_id>", methods=["DELETE"])
@login_required
def user_web_note_delete(username, note_id):
    note = PeterboyNote.query.join(User).filter(
        User.username == username, PeterboyNote.id == note_id).first()

    # 로그인한 사용자만 지우도록
    if current_user.username == username:
        db_session.delete(note)

    return jsonify(success=True)


@app.route("/favicon.ico")
def favicon_ico():
    return abort(404)


app.add_url_rule('/api/1.0', view_func=UserAuthAPI.as_view('user_auth'))
app.add_url_rule('/api/1.0/<username>', view_func=UserDetailAPI.as_view('user_detail'))
app.add_url_rule('/api/1.0/<username>/notes', view_func=UserNotesAPI.as_view('user_notes'))
app.add_url_rule('/api/1.0/<username>/notes/<note_id>', view_func=UserNoteAPI.as_view('user_note'))
app.add_url_rule('/mypage', view_func=MyPage.as_view('mypage'))
app.add_url_rule('/logout', view_func=Logout.as_view('logout'))


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


@app.template_filter()
def date_transform(s):
    parse_date = parse(s)
    return parse_date.strftime('%Y-%m-%d %H:%M:%S')


@app.template_filter()
def tomboytohtml(s):
    parser = xml.sax.make_parser()
    handler = TomboyXMLHandler()
    parser.setContentHandler(handler)

    tmp_xml = io.StringIO()
    tmp_xml.write('<doc>{}</doc>'.format(s))
    tmp_xml.seek(0)

    parser.parse(tmp_xml)
    return Markup("".join(handler.transform))


@app.context_processor
def utility_processor():
    def notebooks():
        records = db_session.query(PeterboyNote.tags)
        tags = [
            {"title": '모든 쪽지',
             "href": url_for('user_web_notes', username=current_user.username)},
            {"title": '분류되지 않은 쪽지',
             "href": url_for('user_web_notes', username=current_user.username,
                             notebook='untagged')}
        ]

        for entry in records:
            notebook = tuple(filter(lambda x: 'system:notebook' in x, entry[0]))
            if notebook:
                notebook_name = notebook[0][16:]
                link = {"title": notebook_name,
                        "href": url_for('user_web_notes',
                                        username=current_user.username,
                                        notebook=notebook_name)}
                if link not in tags:
                    tags.append(link)

        return tags
    return dict(notebooks=notebooks)
