import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'USERS'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    current_guess = sqlalchemy.Column(sqlalchemy.Integer)
    total_guess = sqlalchemy.Column(sqlalchemy.Integer)
    entered_in_contest = sqlalchemy.Column(sqlalchemy.Boolean)
    times_played = sqlalchemy.Column(sqlalchemy.Integer)
    points = sqlalchemy.Column(sqlalchemy.Integer)
    whitelisted = sqlalchemy.Column(sqlalchemy.Boolean)

    def __init__(self, **kwargs):
        self.entered_in_contest = False
        self.times_played = 0
        self.points = 0
        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])


class Quote(Base):
    __tablename__ = 'QUOTES'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    quote = sqlalchemy.Column(sqlalchemy.String)


class AutoQuote(Base):
    __tablename__ = 'AUTOQUOTES'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    quote = sqlalchemy.Column(sqlalchemy.String)
    period = sqlalchemy.Column(sqlalchemy.Integer)


class MiscValue(Base):
    __tablename__ = 'MISC-VALUES'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    mv_key = sqlalchemy.Column(sqlalchemy.String)
    mv_value = sqlalchemy.Column(sqlalchemy.String)


class Command(Base):
    __tablename__ = 'COMMANDS'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    call = sqlalchemy.Column(sqlalchemy.String)
    response = sqlalchemy.Column(sqlalchemy.String)
    permissions = relationship('Permission', backref='COMMANDS')


class Permission(Base):
    __tablename__ = 'PERMISSIONS'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    command_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(Command.id))
    user_entity = sqlalchemy.Column(sqlalchemy.String)
