from authlib.flask.oauth1.sqla import OAuth1ClientMixin, \
    OAuth1TemporaryCredentialMixin, OAuth1TokenCredentialMixin
from sqlalchemy import Column, Integer, ForeignKey, String, Text, Float, DateTime, Boolean, CHAR, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref

from peterboy.database import Base, db_session


class User(Base):
    __tablename__ = 'peterboy_user'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), comment='사용자 ID')
    current_sync_guid = Column(String(36), comment='싱크 고유키', doc='변경시 모든 노트 지워야 함')
    user_mail = Column(String(200), comment='이메일 주소')
    name = Column(String(100), comment='사용자 이름')
    userpw = Column(String(100), comment='사용자 비밀번호')
    persistent_del_yn = Column(CHAR(1), default='Y', comment='영구 삭제 여부')
    create_date = Column(DateTime, default=func.now(), comment='생성일자')

    def get_user_id(self):
        return self.id

    @hybrid_property
    def is_active(self):
        return True

    @hybrid_property
    def is_authenticated(self):
        return True

    def get_id(self):
        return self.username

    @hybrid_property
    def is_anonymous(self):
        return False


class Client(Base, OAuth1ClientMixin):
    __tablename__ = 'client'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('peterboy_user.id', ondelete='CASCADE'))
    user = relationship('User')


class TemporaryCredential(Base, OAuth1TemporaryCredentialMixin):
    __tablename__ = 'temporarycredential'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('peterboy_user.id', ondelete='CASCADE'))
    user = relationship('User')


class TokenCredential(Base, OAuth1TokenCredentialMixin):
    __tablename__ = 'tokencredential'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('peterboy_user.id', ondelete='CASCADE'))
    user = relationship('User')


class TimestampNonce(Base, OAuth1TokenCredentialMixin):
    __tablename__ = 'timestampnonce'

    id = Column(Integer, primary_key=True)
    nonce = Column(String(50), comment="nonce")
    timestamp = Column(String(100), comment="timestamp")


class PeterboyNote(Base):
    __tablename__ = 'peterboy_note'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), comment='고유키')
    user_id = Column(Integer, ForeignKey('peterboy_user.id', ondelete='CASCADE'))
    title = Column(String(255), comment='노트 제목')
    title_slug = Column(Text, comment='노트 제목(Slugify')
    note_content = Column(Text, comment="노트 내용")
    note_content_version = Column(Float, default=0.1, comment='노트 버전')
    last_change_date = Column(String(33), comment="노트 변경일")
    last_metadata_change_date = Column(String(33), comment='노트 정보 변경일')
    create_date = Column(String(33), comment='노트 생성일')
    last_sync_revision = Column(Integer, default=1, comment='노트 싱크 리비전')
    open_on_startup = Column(Boolean, comment='톰보이 실행시 같이 보여줄지 여부')
    pinned = Column(Boolean, comment='노트 고정 여부')
    tags = Column(JSON, comment='태그')
    notebook = relationship("PeterboyNotebook", back_populates="note")

    def toTomboy(self, hidden_last_sync_revision=False):
        resp = {
            'guid': self.guid,
            'title': self.title,
            'note-content': self.note_content,
            'note-content-version': self.note_content_version,
            'last-change-date': self.last_change_date,
            'last-metadata-change-date': self.last_metadata_change_date,
            'create-date': self.create_date,
            'open-on-startup': self.open_on_startup,
            'pinned': self.pinned,
            'tags': self.tags,
            'last-sync-revision': self.last_sync_revision
        }

        if hidden_last_sync_revision:
            del resp['last-sync-revision']

        return resp


class PeterboySync(Base):
    __tablename__ = 'peterboy_sync'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('peterboy_user.id', ondelete='CASCADE'))
    latest_sync_revision = Column(Integer, default=0, comment='마지막 싱크 리비전')

    @classmethod
    def get_latest_revision(cls, user_id):
        record = cls.query.filter(cls.user_id == user_id).first()
        if not record:
            return -1
        else:
            return record.latest_sync_revision

    @classmethod
    def commit_revision(cls, user_id):
        record = cls.query.filter(cls.user_id == user_id).first()
        if not record:
            record = cls()
            record.user_id = user_id
            record.latest_sync_revision = 0

            db_session.add(record)

        record.latest_sync_revision += 1

        return record.latest_sync_revision


class PeterboySyncServer(Base):
    """당분간 사용하지 않겠지만 우선 생성은 해둠(언제 어떻게 쓰게 될지 몰라서...)"""
    __tablename__ = 'peterboy_sync_config'

    config_key = Column(String(100), primary_key=True, comment='설정 키')
    config_value = Column(String(255), primary_key=True, comment='설정 값')

    @classmethod
    def get_config(cls, key_name, default):
        try:
            record = cls.query.filter(cls.config_key == key_name).first()
            if record:
                return record.config_value
            return default
        except (OperationalError, ProgrammingError):
            return default


class PeterboyNotebook(Base):
    __tablename__ = 'peterboy_notebook'

    id = Column(Integer, primary_key=True)
    notebook_name = Column(String(255), comment='쪽지함 이름')
    note_id = Column(Integer, ForeignKey("peterboy_note.id"), comment='쪽지 ID')
    note = relationship("PeterboyNote", back_populates="notebook")
