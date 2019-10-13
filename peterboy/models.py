from authlib.flask.oauth1.sqla import OAuth1ClientMixin, \
    OAuth1TemporaryCredentialMixin, OAuth1TokenCredentialMixin
from sqlalchemy import Column, Integer, ForeignKey, String, Text, Float, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship

from peterboy.database import Base


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), comment='사용자 ID')

    def get_user_id(self):
        return self.id


class Client(Base, OAuth1ClientMixin):
    __tablename__ = 'client'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    user = relationship('User')


class TemporaryCredential(Base, OAuth1TemporaryCredentialMixin):
    __tablename__ = 'temporarycredential'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    user = relationship('User')


class TokenCredential(Base, OAuth1TokenCredentialMixin):
    __tablename__ = 'tokencredential'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    user = relationship('User')


class TimestampNonce(Base, OAuth1TokenCredentialMixin):
    __tablename__ = 'timestampnonce'

    id = Column(Integer, primary_key=True)
    nonce = Column(String(50), comment="nonce")
    timestamp = Column(String(100), comment="timestamp")


def set_user_id(self, user_id):
    self.user_id = user_id


class PeterboyNote(Base):
    __tablename__ = 'peterboy_note'

    guid = Column(String(36), comment='고유키', primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    title = Column(String(255), comment='노트 제목')
    note_content = Column(Text, comment="노트 내용")
    note_content_version = Column(Float, default=0.1, comment='노트 버전')
    last_change_date = Column(String(33), comment="노트 변경일")
    last_metadata_change_date = Column(String(33), comment='노트 정보 변경일')
    create_date = Column(String(33), comment='노트 생성일')
    last_sync_revision = Column(Integer, comment='노트 리비전')
    open_on_startup = Column(Boolean, comment='톰보이 실행시 같이 보여줄지 여부')
    pinned = Column(Boolean, comment='노트 고정 여부')
    tags = Column(JSON, comment='태그')

    def toTomboy(self):
        return {
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
            'last-sync-revision': 1
        }


class PeterboySync(Base):
    __tablename__ = 'peterboy_sync'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    latest_sync_revision = Column(Integer, comment='마지막 싱크 리비전')


class PeterboySyncServer(Base):
    __tablename__ = 'peterbody_sync_config'

    config_key = Column(String(100), primary_key=True, comment='설정 키')
    config_value = Column(String(255), primary_key=True, comment='설정 값')

    @classmethod
    def get_config(cls, key_name):
        record = cls.query.filter(cls.config_key == key_name).first()
        if record:
            return record.config_value
        return ''
