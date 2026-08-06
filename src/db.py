from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.orm import sessionmaker, declarative_base  # type: ignore
from contextlib import contextmanager

from settings import DATABASE_URL, debug

engine = create_engine(DATABASE_URL, echo=debug, pool_size=10, max_overflow=20)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

@contextmanager
def session_scope():
    s = Session()
    try:
        yield s
    finally:
        s.close()
