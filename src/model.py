#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""""""

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB,INT4RANGE
from pgvector.sqlalchemy import Vector  # type: ignore

from db import Base, Session, engine

# vdims = 384
vdims = 768

###

class HistoricalText(Base):
    __tablename__ = "historical_texts"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    path      = Column(String, nullable=False)
    filename  = Column(String, nullable=False)
    text      = Column(ARRAY(JSONB), nullable=False)
    chapters  = Column(ARRAY(JSONB), nullable=False)

    __table_args__ = (
        UniqueConstraint("path", "filename"),
    )

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})
    
class ConvertIndexHistorical(Base):
    __tablename__ = "convert_index_historical"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    textId              = Column(Integer,ForeignKey("historical_texts.id"),nullable=False)
    lineIndex           = Column(Integer,nullable=False)
    lineRange           = Column(String,nullable=False)
    wordIndexRange      = Column(INT4RANGE,nullable=False)

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})

class ConvertIndexBiblical(Base):
    __tablename__ = "convert_index_biblical"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    textId              = Column(Integer,ForeignKey("biblical_texts.id", ondelete="CASCADE"),nullable=False)
    lineIndex           = Column(Integer,nullable=False)
    lineRange           = Column(String,nullable=False)
    wordIndexRange      = Column(INT4RANGE,nullable=False)

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})

class BiblicalText(Base):
    __tablename__ = "biblical_texts"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    path      = Column(String, nullable=False)
    filename  = Column(String, nullable=False)
    text      = Column(ARRAY(JSONB), nullable=False)
    chapters  = Column(ARRAY(JSONB), nullable=False)

    __table_args__ = (
        UniqueConstraint("path", "filename"),
    )

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != "password_hash"})

class HighlightColors(Base):
    __tablename__ = "highlight_colors"

    id = Column(Integer, primary_key=True, autoincrement=True)

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})

class TextHighlights(Base):
    __tablename__ = "text_highlights"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    color_id              = Column(Integer,ForeignKey("highlight_colors.id"),nullable=False)
    historical_text_id    = Column(Integer,ForeignKey("historical_texts.id"),nullable=False)
    biblical_text_id      = Column(Integer,ForeignKey('biblical_texts.id', ondelete="CASCADE"),nullable=False)
    biblical_range_word   = Column(INT4RANGE,nullable=False)
    historical_range_word = Column(INT4RANGE,nullable=False)
    biblical_start_line   = Column(Integer,ForeignKey("convert_index_biblical.id"),nullable=False)
    historical_start_line = Column(Integer,ForeignKey("convert_index_historical.id"),nullable=False)

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})

###

class Verse(Base):
    """Corpus representation, used by all methods for better performance"""

    __tablename__ = "verses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String)
    filename = Column(String)
    address = Column(String)
    text = Column(String, default="")
    lemmas = Column(String, default="")

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})


class Ngram(Base):
    """Used by the N-gram and BM25 (latter uses 1-grams only), pos is used for uniqueness validation only"""

    __tablename__ = "ngrams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lemmas = Column(String)
    text = Column(String)
    n = Column(Integer)
    pos = Column(Integer)

    verse_id = Column(Integer, ForeignKey("verses.id"))

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})


class Embedding(Base):
    """Used only by the strans methods. This is the source of knowledge about available models"""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model = Column(String)
    vector = mapped_column(Vector(vdims))

    verse_id = Column(Integer, ForeignKey("verses.id"))

    def __str__(self):
        return str({c.name: getattr(self, c.name) for c in self.__table__.columns})


def init():
    # print("Creating database at: %s" % DATABASE_URL)
    Base.metadata.create_all(engine)

    s = Session()


def preview():
    from eralchemy2 import render_er  # type: ignore

    render_er(Base, "model.png")


if __name__ == "__main__":
    init()
    # try:
    preview()
    # except:
    #    pass
