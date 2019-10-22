from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine_url = 'postgresql+psycopg2://peterboy:peterboy@localhost:5432/peterboy'
# engine_url = 'postgresql+psycopg2://jiho:dmsthfl@localhost:5432/jiho'

engine = create_engine(engine_url, convert_unicode=True, echo=False)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import peterboy.models
    Base.metadata.create_all(bind=engine)
