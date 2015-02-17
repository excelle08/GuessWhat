drop database if exists atomsquare_unidata;

create database atomsquare_unidata;

use atomsquare_unidata;

create table a_usrs (
    `t_uid` INT(10) NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `t_username` varchar(32) not null,
    `t_password` varchar(32) not null,
    `t_emailaddr` varchar(128) not null,
    `t_gender` tinyint(2) not null,
    `t_qqid` varchar(12),
    `t_cellphone` varchar(11),
    `t_zipcode` varchar(6),
    `t_privilege` tinyint(1),
    `t_rank` tinyint(2),
    `t_avatar` text,
    `t_motto` varchar(200),
    `t_website` varchar(72),
    `t_created_at` real
) engine=innodb default charset=utf8;

create table a_peerlist (
    `t_uid` int(10) not null primary key,
    `t_friends` text,
    `t_blocked` text
) engine=innodb default charset=utf8;

create table a_usrext (
    `t_uid` int(10) not null primary key,
    `t_credits` int(10)
) engine=innodb default charset=utf8;
