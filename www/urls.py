__author__ = 'Excelle'


from core.web import get, view, post, ctx, interceptor, SeeOther, NotFound
from model import User, PeerList, UserExt
from config.config import configs
from apis import api
from apis import APIError, APIPermissionError, APIResourceNotFoundError, APIValueError
from imgsaver import parseImage
import re, time, logging, string
import hashlib
import captcha

_RE_MD5 = re.compile(r'^[0-9a-fA-F]{32}$')
_RE_EMAIL = re.compile(r'^[\w\.\-]+@[\w\-]+(\.[\w\-]+){1,4}$')
_RE_TEXT = re.compile(r'^[\w\s\.\-/\u0391-\uFFE5]+$')
_COOKIE_NAME = 'atomsession'
_COOKIE_KEY = configs.session.secret

# Create a session cookie
def make_signed_cookie(id, password, max_age):
    expires = str(int(time.time() + (max_age or 86400)))
    L = [id, expires, hashlib.md5('%s-%s-%s-%s' % (id, password, expires, _COOKIE_KEY)).hexdigest()]
    return '-'.join(L)

# Identify a retrieved cookie
def parse_signed_cookie(cookie_str):
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        id, expires, md5 = L
        if int(expires) < time.time():
            return None
        user = User.find_first('where t_uid=?', id)
        if user is None:
            return None
        if md5 != hashlib.md5('%s-%s-%s-%s' % (id, user.t_password, expires, _COOKIE_KEY)).hexdigest():
            return None
        return user
    except Exception, e:
        logging.info(e.message)
        return None

# Filter illegal character to avoid XSS risk
def validSecureData(data, field='the field'):
    result = _RE_TEXT.match(data)
    if data == '':
        return data
    if result:
        return data
    else:
        raise APIValueError('text', message='Illegal character in ' + field)

@interceptor('/')
def user_interceptor(next):
    logging.info('Trying to retrieve info from SESSION cookie...')
    user = None
    usrext = None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    if cookie:
        logging.info('Cookie found. Trying to parse data...')
        user = parse_signed_cookie(cookie)
        if user:
            logging.info('Login as <%s>...' % user.t_emailaddr)
            usrext = UserExt.find_first('where t_uid=?', user.t_uid)
    ctx.request.user = user
    ctx.request.usrext = usrext
    return next()

@interceptor('/admin')
def admin_interceptor(next):
    user = ctx.request.user
    if user and user.t_privilege > 2:
        return next()
    raise SeeOther('/')

@api
@post('/api/users')
def register_user():
    i = ctx.request.input(name="", email="", password="", captcha="")
    username = validSecureData(i.name.strip())
    email = validSecureData(i.email.strip().lower())
    password = i.password.strip()
    captcha = i.captcha.strip()
    if ctx.captcha.lower() != captcha:
        raise APIError('register:failed', 'captcha', 'Wrong Captcha.'+ captcha)
    if not username:
        raise APIValueError('username', message="No username")
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email', message="Invalid email")
    if not password or not _RE_MD5.match(password):
        raise APIValueError('password', message="Invalid Hashvalue")
    user = User.find_first('where t_emailaddr=?', email)
    if user:
        raise APIValueError('email', message="EMail is already in use.")
    # Insert into db.
    user = User(username=username, email=email, password=password,
                avatar='/resources/images/user_default.gif', creation_time=time.time())
    user.insert()
    _current_user = User.find_first('where t_emailaddr=?', email)
    friendlist_init = PeerList(id=_current_user['t_uid'], friends='', blocked='')
    friendlist_init.insert()
    ext = UserExt(id=_current_user['t_uid'], credits=0)
    ext.insert()
    # Login as registered user.
    cookie = make_signed_cookie(str(_current_user['t_uid']), user.password, None)
    ctx.response.set_cookie(_COOKIE_NAME, cookie)
    return user

@api
@post('/api/auth')
def authenticate_user():
    i = ctx.request.input()
    email = i.email.strip().lower()
    password = i.password.strip()
    remember = i.remember
    user = User.find_first('where t_emailaddr=?', email)
    if user is None:
        raise APIError('auth:failed', 'email', 'User doesn\'t exist.')
    elif user.t_password != password:
        raise APIError('auth:failed', 'password', 'Wrong password.')
    max_age = 604800
    cookie = make_signed_cookie(str(user.t_uid), user.t_password, max_age)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=(max_age if remember else None))
    user.password = '********'
    return user

@api
@post('/api/user/basicinfo')
def edit_username():
    i = ctx.request.input()
    new_username = validSecureData(i.username)
    user = ctx.request.user
    user.username = new_username
    user.update()
    return user

@api
@post('/api/avatar')
def upload_avatar():
    i = ctx.request.input()
    path = parseImage(i.content)
    user = ctx.request.user
    user.avatar = path
    user.update()
    return user

@api
@post('/api/user/ext')
def edit_extinfo():
    i = ctx.request.input()
    gender = i.gender
    birthday = i.birthday
    qq = validSecureData(i.qq, 'QQ')
    telephone = validSecureData(i.telephone, 'Telephone')
    zipcode = validSecureData(i.zipcode, 'Zipcode')
    website = validSecureData(i.website, 'Website')
    motto = validSecureData(i.motto, 'Motto')
    user_ext = ctx.request.usrext
    user_info = ctx.request.user
    if birthday: user_ext.birthday = birthday
    user_info.gender = gender
    if qq: user_info.qq = qq
    if telephone: user_info.cellphone = telephone
    if zipcode: user_info.zipcode = zipcode
    if website: user_info.website = website
    if motto: user_info.motto = motto
    user_ext.update()
    user_info.update()
    return dict(user=user_info, usrext=user_ext)


@get('/api/captcha')
def get_captcha():
    cap, img = captcha.generateCaptcha()
    ctx.captcha = cap
    ctx.response.content_type = "image/gif"
    return img.getvalue()

@get('/')
def index_page_redirections():
    if ctx.request.user:
        raise SeeOther('/user/basicinfo')
    else:
        raise SeeOther('/register')

@get('/signout')
def signout():
    ctx.response.delete_cookie(_COOKIE_NAME)
    raise SeeOther('/signin')

@view('register.html')
@get('/register')
def register():
    return dict()

@view('login.html')
@get('/signin')
def login():
    return dict()

@view('user_basicinfo.html')
@get('/user/basicinfo')
def edit_basicinfo():
    return dict(user=ctx.request.user, usrext=ctx.request.usrext)

@view('user_avatar.html')
@get('/user/avatar')
def edit_avatar():
    return dict(user=ctx.request.user)

@view('user_ext.html')
@get('/user/ext')
def edit_extension():
    return dict(user=ctx.request.user, usrext=ctx.request.usrext)