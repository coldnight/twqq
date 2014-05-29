#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/12 14:55:02
#   Desc    :
#
import inspect
import logging

from abc import abstractmethod

from .hub import RequestHub
from .requests import BeforeLoginRequest
from .requests import (group_message_handler, buddy_message_handler,
                       kick_message_handler, sess_message_handler,
                       system_message_handler, discu_message_handler)

logger = logging.getLogger("twqq")


class WebQQClient(object):

    """ Webqq 模拟客户端

    :param qq: QQ号
    :param pwd: 密码
    """

    def __init__(self, qq, pwd, debug=False):
                # self.msg_disp = MessageDispatch(self)
        self.setup_msg_handlers()
        self.setup_request_handlers()
        self.hub = RequestHub(qq, pwd, self, debug, handle_msg_image=False)

    @abstractmethod
    def handle_verify_code(self, path, r, uin):
        """ 重写此函数处理验证码

        :param path: 验证码图片路径
        :param r: 接口返回
        :param uin: 接口返回
        """
        pass

    def enter_verify_code(self, code, r, uin):
        """ 填入验证码

        :param code: 验证码
        """
        self.hub.check_code = code.strip().lower()
        pwd = self.hub.handle_pwd(r, self.hub.check_code.upper(), uin)
        self.hub.load_next_request(BeforeLoginRequest(pwd))

    @group_message_handler
    def log_group_message(self, member_nick, content, group_code,
                          send_uin, source):
        """ 对群消息进行日志记录

        :param member_nick: 群昵称
        :param content: 消息内容
        :param group_code:组代码
        :param send_uin: 发送人的uin
        :param source: 消息原包
        """
        logger.info(u"[群消息] {0}: {1} ==> {2}"
                    .format(group_code, member_nick, content))

    @buddy_message_handler
    def log_buddy_message(self, from_uin, content, source):
        """ 对好友消息进行日志记录

        :param from_uin: 发送人uin
        :param content: 内容
        :param source: 消息原包
        """
        logger.info(u"[好友消息] {0} ==> {1}"
                    .format(from_uin, content))

    @sess_message_handler
    def log_sess_message(self, qid, from_uin, content, source):
        """ 记录临时消息日志

        :param qid: 临时消息的qid
        :param from_uin: 发送人uin
        :param content: 内容
        :param source: 消息原包
        """
        logger.info(u"[临时消息] {0} ==> {1}"
                    .format(from_uin, content))

    @discu_message_handler
    def log_discu_message(self, did, from_uin, content, source):
        """ 记录讨论组消息日志

        :param did: 讨论组id
        :param from_uin: 消息发送人 uin
        :param content: 内容
        :param source: 源消息
        """
        logger.info(u"[讨论组消息] {0} ==> {1}"
                    .format(did, content))

    @kick_message_handler
    def log_kick_message(self, message):
        """ 被T除的消息
        """
        logger.info(u"其他地方登录了此QQ{0}".format(message))

    @system_message_handler
    def log_system_message(self, typ, from_uin, account, source):
        """ 记录系统消息日志
        """
        logger.info("[系统消息]: 类型:{0}, 发送人:{1}, 发送账号:{2}, 源:{3}"
                    .format(type, from_uin, account, source))

    def setup_msg_handlers(self):
        """ 获取消息处理器, 获取被 twqq.requests.*_message_handler装饰的成员函数

        """
        msg_handlers = {}
        for _, handler in inspect.getmembers(self, callable):
            if not hasattr(handler, "_twqq_msg_type"):
                continue

            if handler._twqq_msg_type in msg_handlers:
                msg_handlers[handler._twqq_msg_type].append(handler)
            else:
                msg_handlers[handler._twqq_msg_type] = [handler]

        self.msg_handlers = msg_handlers

    def setup_request_handlers(self):
        """ 获取请求处理器(被twqq.reqeusts.register_request_handler 装饰的函数)
        """
        request_handlers = {}
        for _, handler in inspect.getmembers(self, callable):
            if not hasattr(handler, "_twqq_request"):
                continue

            if handler._twqq_request in request_handlers:
                request_handlers[handler._twqq_request].append(handler)
            else:
                request_handlers[handler._twqq_request] = [handler]

        self.request_handlers = request_handlers

    def connect(self):
        self.hub.connect()

    def disconnect(self):
        self.hub.disconnect()

    def run(self):
        if not self.hub.connecting:
            self.connect()
        self.hub.http.start()
