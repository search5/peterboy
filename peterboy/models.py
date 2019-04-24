from authlib.flask.oauth1.sqla import OAuth1ClientMixin, \
    OAuth1TemporaryCredentialMixin, OAuth1TokenCredentialMixin
from sqlalchemy import Column, Integer, ForeignKey, String
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
