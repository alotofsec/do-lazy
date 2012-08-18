#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os

import ConfigParser

config = ConfigParser.ConfigParser()
config.read("d2/config")
db_id = config.get('db', 'db_id')
db_password = config.get('db', 'db_password')
db_name = config.get('db', 'db_name')
app_secret_key = config.get('app', 'app_secret_key')
file_upload_path = config.get('app','file_upload_path')
debug_mode = config.get('app', 'debug_mode')
per_page = int(config.get('app', 'per_page'))
port = config.get('app', 'port')
max_title_string = int(config.get('board', 'max_title_string'))
max_nick_name_string = int(config.get('board', 'max_nick_name_string'))

import hashlib
from datetime import datetime
from flask import Flask, render_template, request, flash, url_for, redirect, make_response, current_app, g
from wtforms import Form, BooleanField, TextField, PasswordField, TextAreaField, validators
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser,
                            confirm_login, fresh_login_required)
from flaskext.cache import Cache

app = Flask(__name__)
memcached = Cache(app)
app.secret_key = app_secret_key
app.config.from_object(__name__)
app.config.update(DEBUG=True)
app.config['CACHE_TYPE'] = 'memcached'
app.config['CACHE_DEFAULT_TIMEOUT'] = 60
app.config['CACHE_MEMCACHED_SERVERS'] = '127.0.0.1:11211'

if debug_mode:
    from werkzeug import SharedDataMiddleware
    import os
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
      '/': os.path.join(os.path.dirname(__file__), 'static') })
    upload_url = os.path.basename( file_upload_path )
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
      '/': os.path.join(os.path.dirname(__file__),  upload_url) })

from werkzeug.contrib.cache import MemcachedCache
cache = MemcachedCache(['127.0.0.1:11211'])

import redis
redis = redis.StrictRedis(host='localhost', port=6379, db="oneline")

class Anonymous(AnonymousUser):
    nick_name = u"anonymous"

login_manager = LoginManager()

login_manager.anonymous_user = Anonymous
login_manager.login_view = "login"
login_manager.login_message = u"Please log in to access this page."
login_manager.refresh_view = "reauth"
login_manager.setup_app(app)

@login_manager.user_loader
def load_user(userid):
    return session.query(User).filter_by(id=userid).first()
    if user:
        return User(userid)
    else:
        return None

from sqlalchemy import create_engine, MetaData, Column, Integer, String, UnicodeText, ForeignKey, desc, func
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, sessionmaker, relationship, backref
from sqlalchemy.types import DateTime, Boolean

engine = create_engine('mysql://%s:%s@localhost/%s?charset=utf8' %  (db_id, db_password, db_name))

Base = declarative_base()
sql_datetime = DateTime

from flaskext.babel import Babel
babel = Babel(app)
app.config['BABEL_DEFAULT_LOCALE'] = 'ko'

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    if user is not None:
        return user.locale
    # otherwise try to guess the language from the user accept
    # header the browser transmits.  We support de/fr/en in this
    # example.  The best match wins.
    return request.accept_languages.best_match(['ko', 'en'])




class SiteInfo(Base):
    __tablename__ = "site-info"
    id = Column(Integer, primary_key=True)
    site_title = Column(String(length=50), nullable = False)
    site_slogan = Column(String(length=200), nullable = False)
    site_desc = Column(String(length=200), nullable = False)
    site_root = Column(String(length=50), nullable = False)

    def __init__(self, site_title, site_slogan, site_desc, site_root):
        self.site_title = site_title
        self.site_slogan = site_slogan
        self.site_desc = site_desc
        self.site_root = site_root

class SiteMenu(Base):
    __tablename__ = "site-menu"
    id = Column(Integer, primary_key=True)
    menu_title = Column(String(length=50), nullable = False)
    menu_link = Column(String(length=50), nullable = False)

    def __init__(self, menu_title, menu_link):
        self.menu_title = menu_title
        self.menu_link = menu_link

class User(Base, UserMixin):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    user_name = Column(String(length=20), nullable = False)
    nick_name = Column(String(length=20), nullable = False)
    email = Column(String(length=50), nullable = False)
    password = Column(String(length=64), nullable = False)
    creat_date = Column(DateTime)
    login_date = Column(DateTime)
    access_date = Column(DateTime)
    is_confirm = Column(Boolean, nullable=True)
    signature = Column(String(length=1000), nullable = True)
    icon_url = Column(String(length=256), nullable = True)
    badge = Column(String(length=200), nullable = True)

    def __init__(self, user_name, nick_name, email, password, 
                creat_date=None, login_date=None, access_date=None, 
                is_confirm=None,
                signature=None, icon_url=None, badge=None):
        self.user_name = user_name
        self.nick_name = nick_name
        self.email = email
        self.password = password
        if creat_date is None:
            creat_date = sql_datetime()
        self.creat_date = creat_date
        if login_date is None:
            login_date = sql_datetime()
        self.login_date = login_date
        if access_date is None:
            access_date = sql_datetime()
        self.access_date = access_date
        self.is_confirm = is_confirm
        self.signature = signature
        self.icon_url = icon_url
        self.badge = badge

class Board(Base):
    __tablename__ = 'board'
    id = Column(Integer, primary_key=True)
    board_id = Column(String(length=20), nullable = False)
    board_name = Column(String(length=20), nullable = False)
    board_desc = Column(String(length=80), nullable = False)

    def __init__(self, board_id, board_name, board_desc):
        self.board_id = board_id
        self.board_name = board_name
        self.board_desc = board_desc

class Article(Base):
    __tablename__ = 'article'
    id = Column(Integer, primary_key=True)
    board_id = Column(String(length=2), nullable = False)
    user_name = Column(String(length=20), nullable = True)
    nick_name = Column(String(length=20), nullable = True)
    password = Column(String(length=64), nullable = True)
    title = Column(UnicodeText, nullable=False)
    text = Column(UnicodeText, nullable=False)
    creat_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)
    is_notice = Column(Boolean, nullable=True)
    is_public = Column(Boolean, nullable=True)
    is_mobile = Column(Boolean, nullable=True)
    anonymity = Column(Boolean, nullable=False)
    remote_addr = Column(String(length=16), nullable = False)
    thumbs_up = Column(String(length=5), nullable = True)
    thumbs_down = Column(String(length=5), nullable = True)
    hits = Column(Integer)

    def __init__(self, board_id, user_name, nick_name, password, 
                title, text, creat_date, modified_date, is_notice, 
                is_public, is_mobile, anonymity, remote_addr, 
                thumbs_up=0, thumbs_down=0, hits=0):
        self.board_id = board_id
        self.user_name = user_name
        self.nick_name = nick_name
        self.password = password
        self.title = title
        self.text = text
        if creat_date is None:
            creat_date = sql_datetime()
        self.creat_date = creat_date
        if modified_date is None:
            modified_date = sql_datetime()
        self.modified_date = modified_date
        self.is_notice = is_notice
        self.is_public = is_public
        self.is_mobile = is_mobile
        self.anonymity = anonymity
#        if remote_addr is None and has_request_context():
#            remote_addr = request.remote_addr
        self.remote_addr = remote_addr
        self.thumbs_up = thumbs_up
        self.thumbs_down = thumbs_down
        self.hits = hits

class SpamFilter(Base):
    __tablename__= "filter-spam"
    id = Column(Integer, primary_key=True)
    spam_word = Column(String(length=20), nullable = False)
    count = Column(Integer, nullable = True)

    def __init__(spam_word, count):
        self.spam_word = spam_word
        self.count = count

class DenyFilter(Base):
    __tablename__= "filter-deny"
    id = Column(Integer, primary_key=True)
    spam_word = Column(String(length=20), nullable = False)
    count = Column(Integer, nullable = True)

    def __init__(spam_word, count):
        self.spam_word = spam_word
        self.count = count

class IpFilter(Base):
    __tablename__= "filter-ip"
    id = Column(Integer, primary_key=True)
    spam_ip = Column(String(length=20), nullable = False)
    count = Column(Integer, nullable = True)

    def __init__(spam_word, count):
        self.spam_ip = spam_ip
        self.count = count

Session = sessionmaker(bind=engine)
session=Session()
session.begin_nested()

Base.metadata.create_all(engine) 

def encode_md5(content):
    md5 = hashlib.md5()
    md5.update(content)
    return md5.hexdigest()

def encode_sha256(content):
    sha256 = hashlib.sha256()
    sha256.update(content)
    return sha256.hexdigest()

def mobile_check(request):
    if request.user_agent.platform in ['iphone', 'android']:
        return True
    else:
        return False

from math import ceil

class Pagination(object):
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count
    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))
    @property
    def has_prev(self):
        return self.page > 1
    @property
    def has_next(self):
        return self.page < self.pages
    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page


class registration_form(Form):
    user_name = TextField('id', [validators.Length(min=2, max=20)])
    nick_name = TextField('Nick name', [validators.Length(min=2, max=20)])
    email = TextField('Email address', [validators.Length(min=2, max=50)])
    password = PasswordField('password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('confirm Password')

class login_form(Form):
    user_name = TextField('id', [validators.Length(min=2, max=50), 
                                validators.Required()])
    password = PasswordField('Password', [validators.Required()])
    remember = BooleanField('remember')

class profile_form(Form):
#    user_name = current_user.user_name
#    user = session.query(User).filter_by(user_name = user_name).first()
    user_name = TextField('id')

class write_article_form(Form):
    nick_name = TextField('nick name', [validators.Length(max=50), 
                                        validators.Required()])
    password = PasswordField('Password', [validators.Required()])
    title = TextField('title', [validators.Length(max=200), 
                                validators.Required()])
    redactor = TextAreaField('Text', default="")

def board_info():
    rv = cache.get('board_info')
    if rv is None:
        rv = session.query(Board).all()
        cache.set('board_info', rv, timeout=5 * 60 * 60)
    return rv

def site_info():
    rv = cache.get('site_info')
    if rv is None:
        rv = session.query(SiteInfo).first()
        cache.set('site_info', rv, timeout=5 * 60 * 60)
    return rv

def site_menu():
    rv = cache.get('site_menu')
    if rv is None:
        rv = session.query(SiteMenu).all()
        cache.set('site_menu', rv, timeout=5 * 60 * 60)
    return rv

from d2 import views
