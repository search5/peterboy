from flask import jsonify, url_for, request, abort
from flask.views import MethodView

from peterboy.database import db_session
from peterboy.lib import create_ref, authorize_pass, authorize_error
from peterboy.models import PeterboySync, PeterboyNote


class UserAuthAPI(MethodView):
    decorators = [authorize_pass]

    def get(self, token_user=None):
        # 톰보이가 서버 연결 요청 버튼을 누르면 여기로 요청된다.

        resp = {
            "oauth_request_token_url": url_for('request_token', _external=True),
            "oauth_authorize_url": url_for('authorize', _external=True),
            "oauth_access_token_url": url_for('access_token', _external=True),
            "api-version": "1.0"
        }

        if token_user:
            user_ref = create_ref('user_detail', 'user_space',
                                  username=token_user.username)
            resp.update({"user-ref": user_ref})

        return jsonify(resp)


class UserDetailAPI(MethodView):
    decorators = [authorize_error]

    def get(self, username, token_user=None):
        latest_sync_revision = PeterboySync.get_latest_revision(token_user.id)

        notes_ref = create_ref('user_notes', 'user_web_notes',
                              username=token_user.username)

        return jsonify({
            "user-name": username,
            "first-name": username,
            "last-name": username,
            "notes-ref": notes_ref,
            "latest-sync-revision": latest_sync_revision,
            "current-sync-guid": token_user.current_sync_guid
        })


class UserNotesAPI(MethodView):
    decorators = [authorize_error]

    def get(self, username, token_user=None):
        latest_sync_revision = PeterboySync.get_latest_revision(token_user.id)

        since = request.args.get('since', 0, type=int)

        note_records = PeterboyNote.query.filter(PeterboyNote.user_id == token_user.id)
        if 'since' in request.args:
            note_records = note_records.filter(
                PeterboyNote.last_sync_revision > since)

        notes = []

        include_notes = request.args.get('include_notes', default=False,
                                         type=bool)

        for record in note_records:
            if include_notes:
                notes.append(record.toTomboy())
            else:
                ref = create_ref('user_note', 'user_web_note',
                                 username=token_user.username,
                                 note_id=record.id)

                notes.append(dict(
                    guid=record.guid,
                    title=record.title,
                    ref=ref
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
                db_session.delete(exist_note)
                continue

            # 노트 버전이 동일하면 업데이트 하지 않는다
            if exist_note.note_content_version == entry['note-content-version']:
                continue

            exist_note.title = entry['title']
            exist_note.note_content = entry['note-content']
            exist_note.note_content_version = entry['note-content-version']
            exist_note.last_change_date = entry['last-change-date']
            exist_note.last_metadata_change_date = entry[
                'last-metadata-change-date']
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
        print(token_user)
        print(token_user.id)
        latest_sync_revision = PeterboySync.commit_revision(token_user.id)

        db_session.flush()

        # 업데이트된 정보만 내려가도록 변경
        note_records = PeterboyNote.query
        notes = []

        for record in note_records:
            ref = create_ref('user_note', 'user_web_note',
                             username=token_user.username,
                             note_id=record.id)

            notes.append(dict(
                guid=record.guid,
                title=record.title,
                ref=ref
            ))

        return jsonify({
            "latest-sync-revision": latest_sync_revision,
            "notes": notes
        })


class UserNoteAPI(MethodView):
    decorators = [authorize_error]

    def get(self, username, note_id, token_user=None):
        note = PeterboyNote.query.filter(
            PeterboyNote.user_id == token_user.id,
            PeterboyNote.id == note_id).first()

        return jsonify({"note": [note.toTomboy(
            hidden_last_sync_revision=True)]})
