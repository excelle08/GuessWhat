__author__ = 'Excelle'

from core.orm import Model, StringField, IntegerField, TextField, FloatField
from re import split


class User(Model):
    __table__ = 'a_usrs'
    id = IntegerField(primary_key=True, ddl='int(10)', name='t_uid')
    username = StringField(ddl='varchar(32)', name='t_username')
    password = StringField(nullable=False, ddl='varchar(32)', name='t_password')
    email = StringField(nullable=False, updatable=False, ddl='varchar(128)', name='t_emailaddr')
    gender = IntegerField(ddl='tinyint(2)', name='t_gender')
    qq = StringField(ddl='varchar(12)', name='t_qqid')
    cellphone = StringField(ddl='varchar(11)', name='t_cellphone')
    zipcode = StringField(ddl='varchar(6)', name='t_zipcode')
    privilege = IntegerField(ddl='tinyint(1)', default=0, name='t_privilege')
    rank = IntegerField(ddl='tinyint(2)', default=1, name='t_rank')
    avatar = TextField(name='t_avatar')
    motto = StringField(ddl='varchar(200)', name='t_motto')
    website = StringField(ddl='varchar(72)', name='t_website')
    creation_time = FloatField(updatable=False, ddl='real', name='t_created_at')


class PeerList(Model):
    __table__ = 'a_peerlist'
    id = IntegerField(primary_key=True, nullable=False, ddl='int(10)', name='t_uid')
    friends = TextField(name='t_friends')
    blocked = TextField(name='t_blocked')


class UserExt(Model):
    __table__ = 'a_usrext'
    id = IntegerField(primary_key=True, nullable=False, ddl='int(10)', name='t_uid')
    credits = IntegerField(ddl='int(10)', default=0, name='t_credits')
    birthday = FloatField(ddl='real', name='t_birthday')


class Message(Model):
    __table__ = 'a_msg'
    t_id = IntegerField(primary_key=True, ddl='int(10)', name='t_id')
    t_to = IntegerField(nullable=False, ddl='int(10)')
    t_from = IntegerField(nullable=False, ddl='int(10)')
    t_title = StringField(ddl='varchar(80)', name='t_title')
    t_content = TextField()
    t_read = IntegerField(ddl='tinyint(1)', default=0)
    t_time = FloatField(ddl='real')


def GetUIDLists(lst):
    return split(';', lst)