#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import hashlib
import ConfigParser
from math import ceil
from datetime import datetime
from flask import (Flask, render_template, request, flash, url_for, redirect, 
                   make_response, current_app, g)
from wtforms import (Form, BooleanField, TextField, PasswordField, 
                     TextAreaField, validators)
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser,
                            confirm_login, fresh_login_required)
from flask.ext.cache import Cache
from flask.ext.babel import Babel
from werkzeug.contrib.cache import MemcachedCache
import redis
import sqlalchemy
from sqlalchemy import (create_engine, MetaData, Column, Integer, String, 
                        UnicodeText, ForeignKey, desc, func)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, sessionmaker, relationship, backref
from sqlalchemy.types import DateTime, Boolean

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

app = Flask(__name__)
app.secret_key = app_secret_key

babel = Babel(app)
app.config['BABEL_DEFAULT_LOCALE'] = 'ko'

memcached = Cache(app)
app.config.from_object(__name__)
app.config.update(DEBUG=True)
app.config['CACHE_TYPE'] = 'memcached'
app.config['CACHE_DEFAULT_TIMEOUT'] = 60
app.config['CACHE_MEMCACHED_SERVERS'] = '127.0.0.1:11211'

cache = MemcachedCache(['127.0.0.1:11211'])

redis = redis.StrictRedis(host='localhost', port=6379, db="oneline")

engine = create_engine('mysql://%s:%s@localhost/%s?charset=utf8' % 
        (db_id, db_password, db_name))

Base = declarative_base()
sql_datetime = DateTime

Session = sessionmaker(bind=engine)
session=Session()
session.begin_nested()

Base.metadata.create_all(engine) 

if debug_mode:
    from werkzeug import SharedDataMiddleware
    import os
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
      '/': os.path.join(os.path.dirname(__file__), 'static') })
    upload_url = os.path.basename( file_upload_path )
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
      '/': os.path.join(os.path.dirname(__file__),  upload_url) })



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
    board_id = Column(String(length=2), nullable=True)
    user_name = Column(String(length=20), nullable=True)
    nick_name = Column(String(length=20), nullable=True)
    password = Column(String(length=64), nullable=True)
    title = Column(UnicodeText, nullable=True)
    text = Column(UnicodeText, nullable=True)
    creat_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)
    is_notice = Column(Boolean, nullable=True)
    is_public = Column(Boolean, nullable=True)
    is_mobile = Column(Boolean, nullable=True)
    is_anonymous = Column(Boolean, nullable=True)
    remote_addr = Column(String(length=16), nullable=True)
    thumbs_up = Column(String(length=5), nullable=True)
    thumbs_down = Column(String(length=5), nullable=True)
    hits = Column(Integer, nullable=True)

    def __init__(self, board_id=None, user_name=None, nick_name=None, 
                password=None, title=None, text=None, creat_date=None, 
                modified_date=None, is_notice=False, 
                is_public=False, is_mobile=False, is_anonymous=False, 
                remote_addr=None, 
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
        self.is_anonymous = is_anonymous
        self.remote_addr = remote_addr
        self.thumbs_up = thumbs_up
        self.thumbs_down = thumbs_down
        self.hits = hits

class ArticleTemp(Base):
    __tablename__ = 'article-temp'
    id = Column(Integer, primary_key=True)
    board_id = Column(String(length=2), nullable=True)
    user_name = Column(String(length=20), nullable=True)
    nick_name = Column(String(length=20), nullable=True)
    password = Column(String(length=64), nullable=True)
    title = Column(UnicodeText, nullable=True)
    text = Column(UnicodeText, nullable=True)
    creat_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)
    is_notice = Column(Boolean, nullable=True)
    is_public = Column(Boolean, nullable=True)
    is_mobile = Column(Boolean, nullable=True)
    is_anonymous = Column(Boolean, nullable=True)
    remote_addr = Column(String(length=16), nullable=True)
    thumbs_up = Column(String(length=5), nullable=True)
    thumbs_down = Column(String(length=5), nullable=True)
    hits = Column(Integer, nullable=True)

    def __init__(self, board_id=None, user_name=None, nick_name=None, 
                password=None, title=None, text=None, creat_date=None, 
                modified_date=None, is_notice=False, 
                is_public=False, is_mobile=False, is_anonymous=False, 
                remote_addr=None, 
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
        self.is_anonymous = is_anonymous
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

# end / database table set 

# make database table
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


@app.route('/')
@memcached.cached(timeout=60)
def index():
    context =  { 'site_info' : site_info(),
                'site_menu' : site_menu() }
    return render_template('index.html', **context)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = registration_form(request.form)
    context = { 'form' : form, 'site_info' : site_info(), 
                'site_menu' : site_menu() }
    return render_template('register.html', form=form)

@app.route('/register/add', methods=['GET', 'POST'])
def register():
    form = registration_form(request.form)
    if request.method == 'POST' and form.validate():
        creat_date = datetime.now()
        password = encode_sha256(encode_md5
                                (form.password.data+form.user_name.data))
        user = User(form.user_name.data, form.nick_name.data, form.email.data,
                    password, creat_date)
        session.add(user)
        try:
            session.commit()
        except:
            session.rollback() 
        flash('Thanks for registering')
        return redirect(url_for('login'))
    context = { 'form': form, 
                'site_info': site_info(), 'site_menu': site_menu() }
    return render_template('register.html', **context)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = login_form(request.form)
    if request.method == "POST" and form.validate():
        user = session.query(User).filter_by(user_name = form.user_name.data).\
            first()
        if user is None:
            return "no id"
        else:
            input_password = encode_sha256(encode_md5
                                    (form.password.data+form.user_name.data))
            if user.password == input_password:
                user.login_date = datetime.now()                
                try:
                    session.commit()
                except:
                    session.rollback()
                login_user(user)
                return redirect(url_for('index'))
            else:
                return "wrong password"
    context = { 'form' : form, 
                'site_info': site_info(), 'site_menu': site_menu() }
    return render_template("login.html", **context)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/profile/<user_name>")
@login_required
def profile(user_name):
    form = profile_form(request.form)
    user_name = current_user.user_name
    user = session.query(User).filter_by(user_name = user_name).first()
    context = { 'form': form, 
                'site_info': site_info(), 'site_menu': site_menu(),
                'user': user}
    return render_template("profile.html", **context) 

@app.route("/board/<board_name>/page/<int:page>/article/<int:article_number>")
def article_view(board_name, page, article_number):
    article_detail = session.query(Article).filter_by(id = article_number).\
        first()
    # if article is not exist, flash message
    if article_detail is None:
        flash('Sorry. Article is not exist.')
        return redirect(url_for('board_view', board_name=board_name, page=1))
    # article is exist. read database and print
    else:
        board = session.query(Board).\
            filter_by(board_id = article_detail.board_id).first()
        article_detail.hits = article_detail.hits + 1
        session.add(article_detail)
        try:
            session.commit()
        except:
            session.rollback()
        page_now = page
        page = page - 1
        next_page = page + 2
        board = session.query(Board).filter_by(board_name = board_name).first()
        # article number make
        # count public article number
        lastest_article_number = int(session.query(Article).\
            filter(Article.board_id==board.board_id).\
            filter(Article.is_public==True).count())
        total_article_number = int(session.query(Article).\
            filter(Article.board_id==board.board_id).\
            filter(Article.is_public==True).count()) - (page * per_page)
        article_from = int(page) * int(per_page)
        article_to = (int(page) + 1) * int(per_page)
        # extract article list from database 
        article_list = session.query(Article).\
            filter(Article.board_id==board.board_id).\
            order_by(desc(Article.id)).\
            filter(Article.is_public==True)[article_from:article_to]
        # extract notice from database
        notice_list = session.query(Article).\
            filter(Article.board_id==board.board_id).\
            filter(Article.is_notice==True).order_by(desc(Article.id)).\
            filter(Article.is_public==True).all()
        pagination = Pagination(page, per_page, lastest_article_number)
        context = { 'article_list': article_list, 'notice_list': notice_list, 
                    'site_info': site_info, 'board' : board, 
                    'board_name': board_name,
                    'article_detail': article_detail,
                    'max_title_string': max_title_string,
                    'max_nick_name_string': max_nick_name_string,
                    'page' : page, 'per_page': per_page, 'page_now': page_now,
                    'pagination' : pagination, 'next_page': next_page, 
                    'lastest_article_number': lastest_article_number,
                    'total_article_number' : total_article_number,
                    'site_info': site_info(), 'site_menu': site_menu() }
    return render_template("article.html", **context)


@app.route("/board/<board_name>")
@app.route("/board/<board_name>/")
def board(board_name, page=1):
    return redirect(url_for('board_view', board_name=board_name, page=page))
@app.route("/board/<board_name>/page/<int:page>")
@app.route("/board/<board_name>/page/<int:page>/")
def board_view(board_name,page):
    page_now = page
    page = page - 1
    next_page = page + 2
    board = session.query(Board).filter_by(board_name = board_name).first()
    # article number make
    # count public article number
    lastest_article_number = int(session.query(Article).\
        filter(Article.board_id==board.board_id).\
        filter(Article.is_public==True).count())
    total_article_number = int(session.query(Article).\
        filter(Article.board_id==board.board_id).\
        filter(Article.is_public==True).count()) - (page * per_page)
    article_from = int(page) * int(per_page)
    article_to = (int(page) + 1) * int(per_page)
    # extract article list from database 
    article_list = session.query(Article).\
        filter(Article.board_id==board.board_id).order_by(desc(Article.id)).\
        filter(Article.is_public==True)[article_from:article_to]
    # extract notice from database
    notice_list = session.query(Article).\
        filter(Article.board_id==board.board_id).\
        filter(Article.is_notice==True).order_by(desc(Article.id)).\
        filter(Article.is_public==True).all()
    pagination = Pagination(page, per_page, lastest_article_number)
    context = { 'article_list': article_list, 'notice_list': notice_list, 
                'site_info': site_info, 'board' : board, 
                'board_name': board_name,
                'max_title_string': max_title_string,
                'max_nick_name_string': max_nick_name_string,
                'page' : page, 'per_page': per_page, 'page_now': page_now,
                'pagination' : pagination, 'next_page': next_page, 
                'lastest_article_number': lastest_article_number,
                'total_article_number' : total_article_number,
                'site_info': site_info(), 'site_menu': site_menu() }
    return render_template("board.html", **context)

import json
import time
@app.route("/board/upload", methods=["POST"] )
def board_upload():
    if request.method != "POST":
        return "Error"
    file = request.files['file']
    if file and file.filename.endswith(".jpg"):
        secure_filename = str(int(time.time())) + ".jpg"
        file.save( os.path.join( file_upload_path , secure_filename ))
        url_path = "/" + str(os.path.basename( file_upload_path ))
        return json.dumps(
            { "filelink" : os.path.join ( url_path , secure_filename )})
    return json.dumps({})
    #file_upload_path


@app.route("/board/<board_name>/write", methods=["GET", "POST"], 
            defaults={'page_number': 1})
def board_write(board_name, page_number=1):
    form = write_article_form(request.form)
    board = session.query(Board).filter_by(board_name = board_name).first()
    board_id = board.board_id
    creat_date = datetime.now()
    remote_addr = request.remote_addr
    # check temp-save data by ip address
    temp_article_check = session.query(ArticleTemp).\
        filter_by(remote_addr=remote_addr).\
        filter_by(user_name="temp_article").first()
    temp_article = temp_article_check
    # input from post
    if request.method == 'POST':
        if current_user.nick_name == "anonymous":
            user_name = Anonymous.nick_name
            nick_name = form.nick_name.data
            password = encode_sha256(encode_md5(form.password.data+user_name))
            is_anonymous = True 
        else:
            user_name = current_user.user_name
            nick_name = current_user.nick_name
            password = current_user.password
            is_anonymous = False
        title = form.title.data
        text = form.redactor.data
        modified_date = datetime.now()
        is_notice = False
        is_public = True
        is_mobile = mobile_check(request)
        remote_addr = request.remote_addr
        # temp_article update as input data 
        session.query(ArticleTemp).filter_by(remote_addr=remote_addr).\
        filter_by(user_name="temp_article").update(
            {"user_name": user_name,
            "nick_name": nick_name,
            "password": password,
            "title": title,
            "text": text,
            "modified_date": modified_date,
            "is_notice": is_notice,
            "is_public": is_public,
            "is_mobile": is_mobile}
            )
        # read temp_article 
        temp_article = session.query(ArticleTemp).filter_by(title=title).\
        filter_by(nick_name=nick_name).first()
        # commit to article table
        session.add
        flash('article write')
        return redirect(url_for('board_view', board_name=board_name, page=1))
    context = { 'form' : form, 'site_info': site_info(), 
                'board': board,
                'temp_article': temp_article,
                'site_menu': site_menu(),
                'board_name': board_name }
    return render_template("write_article.html", **context)

@app.route("/temp_write", methods=["POST"])
def temp_article_write():
    form = write_article_form(request.form)
    temp_text = request.form['data']
    '''
    form = write_article_form(request.form)
    creat_date = datetime.now()
    board_id = None
    remote_addr = request.remote_addr
    is_mobile = False
    # temp-save chec
    temp_article_check = session.query(ArticleTemp).\
        filter_by(remote_addr=remote_addr).\
        filter_by(user_name="temp_article").first()
    # if temp-save date is not exist, make temp_article
    if temp_article_check is None:
        user_name = "temp_article"
        nick_name = None
        password = None
        title = None
        text = None
        modified_date = None
        is_notice = False
        is_public = False
        is_anonymous = False
        temp_article = ArticleTemp(board_id, user_name, nick_name, password, 
                            title, text, creat_date, modified_date, 
                            is_notice, is_public, is_mobile, is_anonymous, 
                            remote_addr)
        session.add(temp_article)
        try:
            session.commit()
        except:
            session.rollback()
    else:
        board_id = None
        if current_user.nick_name == "anonymous":
            user_name = Anonymous.nick_name
            nick_name = None
            password = None
            is_anonymous = True 
        else:
            user_name = current_user.user_name
            nick_name = current_user.nick_name
            password = current_user.password
            is_anonymous = False
        title = form.title.data
        text = form.redactor.data
        modified_date = datetime.now()
        is_notice = False
        is_public = False
        remote_addr = request.remote_addr
        session.query(ArticleTemp).filter_by(remote_addr=remote_addr).\
        filter_by(user_name="temp_article").update(
            {"user_name": user_name,
            "nick_name": nick_name,
            "password": password,
            "title": title,
            "text": text,
            "modified_date": modified_date,
            "is_notice": is_notice,
            "is_public": is_public,
            "is_mobile": is_mobile}
            )

    if request.method != "POST":
        return "Error"

    form = write_article_form(request.form)
    board_id = None
    creat_date = datetime.now()
    remote_addr = request.remote_addr
    if current_user.nick_name == "anonymous":
        user_name = Anonymous.nick_name
        nick_name = None
        password = None
        is_anonymous = True 
    else:
        user_name = current_user.user_name
        nick_name = current_user.nick_name
        password = current_user.password
        is_anonymous = False
    title = form.title.data
    text = form.redactor.data
    modified_date = datetime.now()
    is_notice = False
    is_public = True
    is_mobile = mobile_check(request)
    remote_addr = request.remote_addr
    # delete before-temp_article data
    temp_article_delete = session.query(ArticleTemp).\
        filter_by(remote_addr=remote_addr).first()
    session.delete(temp_article_delete)
    try:
        session.commit()
    except:
        session.rollback()
    
    # temp_article commit as input data 
    temp_article = ArticleTemp(board_id, user_name, nick_name, password, 
                        title, text, creat_date, modified_date, 
                        is_notice, is_public, is_mobile, is_anonymous, 
                        remote_addr)
    session.add(temp_article)
    try:
        session.commit()
    except:
        session.rollback()
    return flash('auto save')
    '''
@app.route("/rss/article")
def rss_view():
    last_article = session.query(Article).order_by(desc(Article.id)).first()
    article_list = session.query(Article).order_by(Article.id).limit(10)
    return render_template("rss.xml", last_article=last_article, 
                            article_list=article_list, site_info=site_info) 

@app.route("/i")
def write_article():
    site_title = "dolazy"
    site_slogan = "아스카와 나의 신혼방"
    site_desc = "힘겨운 삶의 진통제"
    site_root = "http://rkrk.kr:5001/"
    siteinfo = SiteInfo(site_title, site_slogan, site_desc, site_root)
    session.add(siteinfo)
    try:
        session.commit()
    except:
        session.rollback()

    board_id = 1
    board_name = "신혼방"
    board_desc = "찌질거리는 이를 까지 말라"
    board = Board(board_id, board_name, board_desc)
    session.add(board)
    try:
        session.commit()
    except:
        session.rollback()

    menu_title = "신혼방"
    menu_link = "board/신혼방"
    menu = SiteMenu(menu_title, menu_link)
    session.add(menu)
    try:
        session.commit()
    except:
        session.rollback()

    for i in range(1,40):
        b_name = 1
        board_id = 1
        i = str(i)
        user_name = "user_name" + i
        nick_name = "nick_name" + i
        password = "password" + i
        is_anonymous = False
        title = "title " + i
        text = "text" + i
        creat_date = datetime.now()
        modified_date = datetime.now()
        is_notice = False
        is_public = True
        is_mobile = mobile_check(request)
        remote_addr = request.remote_addr
        article = Article(board_id, user_name, nick_name, password, 
                            title, text, creat_date, modified_date, 
                            is_notice, is_public, is_mobile, is_anonymous, 
                            remote_addr)
        session.add(article)
        try:
            session.commit()
        except:
            session.rollback()
    return unicode("inserted")


