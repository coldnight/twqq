#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/14 13:23:49
#   Desc    :
#
"""
    usage:
        python echobot.py [qq] [password]
"""
import logging

from twqq.client import WebQQClient
from twqq.requests import system_message_handler, group_message_handler
from twqq.requests import buddy_message_handler


logger = logging.getLogger("client")

class Client(WebQQClient):
    def handle_verify_code(self, path, r, uin):
        logger.info(u"验证码本地路径为: {0}".format(path))
        check_code = None
        while not check_code:
            check_code = raw_input("输入验证码: ")
        self.enter_verify_code(check_code, r, uin)


    @system_message_handler
    def handle_friend_add(self, mtype, from_uin, account, message):
        if mtype == "verify_required":
            self.hub.accept_verify(from_uin, account, account)

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        self.hub.send_group_msg(group_code, u"{0}: {1}".format(member_nick, content))

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        self.hub.send_buddy_msg(from_uin, content)


if __name__ == "__main__":
    import sys
    twqqLogger = logging.getLogger("twqq")
    twqqLogger.setLevel(logging.DEBUG)
    webqq = Client(sys.argv[1], sys.argv[2])
    webqq.run()
