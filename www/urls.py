# -*- coding:utf-8 -*-
__author__ = 'Excelle'


from core.web import get, view, post, ctx, interceptor, SeeOther, NotFound
from model import User, PeerList, UserExt, Message
from config.config import configs
from apis import api, Page
from apis import APIError, APIPermissionError, APIResourceNotFoundError, APIValueError
from imgsaver import parseImage
import re, time, logging, string
import hashlib
import captcha

_RE_MD5 = re.compile(r'^[0-9a-fA-F]{32}$')
_RE_EMAIL = re.compile(r'^[\w\.\-]+@[\w\-]+(\.[\w\-]+){1,4}$')
_RE_TEXT = re.compile(r'^[\u0391-\uFFE5\w\s\.\-/]+$', flags=re.UNICODE)
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
    data = data.encode('utf-8')
    result = _RE_TEXT.match(data)
    if data == '':
        return data
    if result:
        return data
    else:
        raise APIValueError('text', message='Illegal character in ' + field)


def _get_page_index():
    page_index = 1
    try:
        page_index = int(ctx.request.get('page', '1'))
    except ValueError:
        pass
    return page_index


def check_admin():
    user = ctx.request.user
    if user and user.t_admin:
        return
    else:
        raise APIPermissionError('Access Denied.')


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

@interceptor('/admincp')
@interceptor('/admincp/')
def admin_interceptor(next):
    user = ctx.request.user
    if user and user.t_privilege:
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

@api
@post('/api/password')
def edit_password():
    i = ctx.request.input()
    captcha = ctx.captcha
    old_password = i.old_pw
    new_password = i.new_pw
    if captcha.lower() != i.captcha:
        raise APIValueError('captcha', message='Captcha is incorrect.')
    if old_password != ctx.request.user.t_password:
        raise APIValueError('org_pwd', message='Your original password is wrong.')
    u = ctx.request.user
    u.t_password = new_password
    u.update()
    return dict()

@api
@post('/api/message/send')
def send_message():
    i = ctx.request.input(to='', subject='', content='')
    user_to = User.find_first('where t_emailaddr=?', i.to)
    to_id = user_to.t_uid
    from_id = ctx.request.user.t_uid
    subject = validSecureData(i.subject)
    content = validSecureData(i.content)
    msg = Message(t_to=to_id, t_from=from_id, t_title=subject, t_content=content, t_read=0, t_time=time.time())
    msg.insert()
    return dict()

@api
@get('/api/message/recv')
def receive_message():
    user = ctx.request.user
    if not user:
        return dict()
    uid = user.t_uid
    total = Message.count_by('where t_to=?', uid)
    page = Page(total, page_index=_get_page_index(), page_size=5)
    msg_list = Message.find_by('where t_to=? order by t_time desc limit ?,?', uid, page.offset, page.limit)
    messages = list()
    for m in msg_list:
        u = User.find_first('where t_uid=?', m.t_from)
        m.t_from = u.t_username
        m['t_fromid'] = u.t_uid
        m['t_fromemail'] = u.t_emailaddr
        messages.append(m)

    return dict(messages=messages, page=page)

@api
@get('/api/friends/get')
def api_get_friendlist():
    current_user = ctx.request.user
    friends_dataobj = PeerList.find_first('where t_uid=?', current_user.t_uid)
    friends_str = friends_dataobj.t_friends
    flist = re.split(';', friends_str)
    count = len(flist)
    page = Page(count, _get_page_index(), page_size=5)
    friends = list()
    for uid in flist:
        u = User.find_first('where t_uid=? order by t_uid desc limit ?,?', uid, page.offset, page.limit)
        if u is None:
            continue
        friends.append(u)
    return dict(user=current_user, friends=friends, page=page)

@api
@post('/api/friends/add')
def api_add_friend():
    current_user = ctx.request.user
    current_peerlist = PeerList.find_first('where t_uid=?', current_user.t_uid)
    i = ctx.request.input(email='')
    target_email = validSecureData(i.email)
    if not target_email:
        raise APIValueError('email', 'Empty email address')
    target_user = User.find_first('where t_emailaddr=?', target_email)
    if target_user is None:
        raise APIValueError('email', 'User doesn\'t exist.')
    current_peerlist.t_friends += (';' + str(target_user.t_uid))
    current_peerlist.update()
    return dict()

@api
@post('/api/friends/del')
def api_del_friend():
    current_user = ctx.request.user
    current_peerlist = PeerList.find_first('where t_uid=?', current_user.t_uid)
    i = ctx.request.input(email='')
    target_email = validSecureData(i.email)
    if not target_email:
        raise APIValueError('email', 'Empty email address')
    target_user = User.find_first('where t_emailaddr=?', target_email)
    if target_user is None:
        raise APIValueError('email', 'User doesn\'t exist.')
    lst = re.split(';', current_peerlist.t_friends)
    lst.remove(str(target_user.t_uid))
    current_peerlist.t_friends = string.join(lst,';')
    current_peerlist.update()
    return dict()

@api
@post('/api/message/:msg_id/read')
def api_mark_read(msg_id):
    msg = Message.get(msg_id)
    if msg is None:
        raise NotFound()
    msg.t_read = 1
    msg.update()
    return dict()

@api
@post('/api/message/:msg_id/delete')
def api_delete_message(msg_id):
    msg = Message.get(msg_id)
    if msg is None:
        raise NotFound()
    msg.delete()
    return dict()

@api
@get('/api/usrlist')
def get_user_list():
    check_admin()
    total = User.count_all()
    page = Page(total, page_index=_get_page_index())
    user_list = User.find_by('order by t_created_at desc limit ?,?', page.offset, page.limit)
    return dict(users=user_list, page=page)

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

@view('user_messages.html')
@get('/peer/messages')
def show_messages():
    return dict(user=ctx.request.user)

@view('user_friends.html')
@get('/peer/friends')
def view_friends():
    return dict(user=ctx.request.user)

@view('user_blocklist.html')
@get('/peer/blocked')
def view_blocklist():
    return dict(user=ctx.request.user)

@view('user_pwd.html')
@get('/user/password')
def change_password():
    return dict(user=ctx.request.user)

@view('user_info.html')
@get('/user/:userid')
def view_user_info(userid):
    u = User.get(userid)
    u_ext = UserExt.get(userid)
    if u is None:
        raise NotFound()
    return dict(user=ctx.request.user, u=u, ext=u_ext)