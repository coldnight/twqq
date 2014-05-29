#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/11 18:21:10
#   Desc    :
#
import os
import json
import time
import random
import inspect
import logging

import const

logger = logging.getLogger("twqq")


class WebQQRequest(object):
    METHOD_POST = "post"
    METHOD_GET = "get"

    hub = None
    url = None
    params = {}
    headers = {}
    method = METHOD_GET         # 默认请求为GET
    kwargs = {}
    ready = True

    def __init__(self, *args, **kwargs):
        self.delay = kwargs.pop("delay", 0)
        self.init(*args, **kwargs)

    def handle_exc(self, type, value, trace):
        pass

    def handle_retcode(self, data, msg):
        if isinstance(data, dict):
            retcode = data.get("retcode")
            if retcode == 0:
                logger.info(u"{0} 成功".format(msg))
            elif retcode == 8:
                logger.error(u"{0} 失败, 需要重新登录".format(msg))

            return

        logger.warn(u"{0} 失败 <{1}>".format(msg, data))


class LoginSigRequest(WebQQRequest):
    url = "https://ui.ptlogin2.qq.com/cgi-bin/login"

    def init(self):
        self.hub.wait()
        logger.info("获取 login_sig...")
        self.params = [("daid", self.hub.daid), ("target", "self"),
                       ("style", 5), ("mibao_css", "m_webqq"),
                       ("appid", self.hub.aid), ("enable_qlogin", 0),
                       ("no_verifyimg", 1),
                       ("s_url", "http://web2.qq.com/loginproxy.html"),
                       ("f_url", "loginerroralert"),
                       ("strong_login", 1), ("login_state", 10),
                       ("t", "20130723001")]

    def callback(self, resp, data):
        if not data:
            logger.warn(u"没有获取到 Login Sig, 重新获取")
            return self.hub.load_next_request(self)

        sigs = self.hub.SIG_RE.findall(resp.body)
        if len(sigs) == 1:
            self.hub.login_sig = sigs[0]
            logger.info(u"获取Login Sig: {0}".format(self.hub.login_sig))
        else:
            logger.warn(u"没有获取到 Login Sig, 后续操作可能失败")

        self.hub.load_next_request(CheckRequest())


class CheckRequest(WebQQRequest):

    """ 检查是否需要验证码
    """
    url = "http://check.ptlogin2.qq.com/check"

    def init(self):
        self.params = {"uin": self.hub.qid, "appid": self.hub.aid,
                       "u1": const.CHECK_U1, "login_sig": self.hub.login_sig,
                       "js_ver": 10040, "js_type": 0, "r": random.random()}
        self.headers.update({"Referer": const.CHECK_REFERER})

    def callback(self, resp, data):
        r, vcode, uin = eval("self.hub." + data.strip().rstrip(";"))
        logger.debug("R:{0} vcode:{1}".format(r, vcode))
        self.hub.clean()
        if int(r) == 0:
            logger.info("验证码检查完毕, 不需要验证码")
            password = self.hub.handle_pwd(r, vcode, uin)
            self.hub.check_code = vcode
            self.hub.load_next_request(BeforeLoginRequest(password))
        else:
            logger.warn("验证码检查完毕, 需要验证码")
            self.hub.require_check = True
            self.hub.load_next_request(VerifyCodeRequest(r, vcode, uin))


class VerifyCodeRequest(WebQQRequest):
    url = "https://ssl.captcha.qq.com/getimage"

    def init(self, r, vcode, uin):
        self.r, self.vcode, self.uin = r, vcode, uin
        self.params = [("aid", self.hub.aid), ("r", random.random()),
                       ("uin", self.hub.qid)]

    def callback(self, resp, data):
        self.hub.require_check_time = time.time()
        with open(self.hub.checkimg_path, 'wb') as f:
            f.write(resp.body)
        self.hub.unwait()

        self.hub.client.handle_verify_code(self.hub.checkimg_path, self.r,
                                           self.uin)


class BeforeLoginRequest(WebQQRequest):

    """ 登录前的准备
    """
    url = "https://ssl.ptlogin2.qq.com/login"

    def init(self, password):
        self.hub.unwait()
        self.hub.lock()
        self.params = [("u", self.hub.qid), ("p", password),
                       ("verifycode", self.hub.check_code),
                       ("webqq_type", 10), ("remember_uin", 1),
                       ("login2qq", 1),
                       ("aid", self.hub.aid), ("u1", const.BLOGIN_U1),
                       ("h", 1), ("action", '4-5-8246'), ("ptredirect", 0),
                       ("ptlang", 2052), ("from_ui", 1),
                       ("daid", self.hub.daid),
                       ("pttype", 1), ("dumy", ""), ("fp", "loginerroralert"),
                       ("mibao_css", "m_webqq"), ("t", 1), ("g", 1),
                       ("js_type", 0),
                       ("js_ver", 10040), ("login_sig", self.hub.login_sig)]
        referer = const.BLOGIN_R_REFERER if self.hub.require_check else\
            const.BLOGIN_REFERER
        self.headers.update({"Referer": referer})

    def ptuiCB(self, scode, r, url, status, msg, nickname=None):
        """ 模拟JS登录之前的回调, 保存昵称 """
        return scode, r, url, status, msg, nickname

    def get_back_args(self, data):
        blogin_data = data.decode("utf-8").strip().rstrip(";")
        logger.info(u"登录返回数据: {0}".format(blogin_data))
        return eval("self." + blogin_data)

    def check(self, scode, r, url, status, msg, nickname=None):
        self.hub.unlock()
        if int(scode) == 0:
            logger.info("从Cookie中获取ptwebqq的值")
            old_value = self.hub.ptwebqq
            try:
                val = self.hub.http.cookie['.qq.com']['/']['ptwebqq'].value
                self.hub.ptwebqq = val
            except:
                logger.error("从Cookie中获取ptwebqq的值失败, 使用旧值尝试")
                self.hub.ptwebqq = old_value
        elif int(scode) == 4:
            logger.error(msg)
            return False, self.hub.load_next_request(CheckRequest())
        else:
            logger.error(u"server response: {0}".format(msg.decode('utf-8')))
            return False, self.hub.load_next_request(CheckRequest())

        if nickname:
            self.hub.nickname = nickname.decode('utf-8')

        return True, url

    def callback(self, resp, data):
        if not data:
            logger.error("没有数据返回, 登录失败, 尝试重新登录")
            return self.hub.load_next_request(CheckRequest())

        args = self.get_back_args(resp.body)
        r, url = self.check(*args)
        if r:
            logger.info("检查完毕")
            self.hub.load_next_request(LoginRequest(url))


class LoginRequest(WebQQRequest):

    """ 登录前的准备
    """

    def init(self, url):
        logger.info("开始登录前准备...")
        self.url = url
        self.headers.update(Referer=const.LOGIN_REFERER)

    def callback(self, resp, data):
        if os.path.exists(self.hub.checkimg_path):
            os.remove(self.hub.checkimg_path)

        self.hub.load_next_request(Login2Request())


class Login2Request(WebQQRequest):

    """ 真正的登录
    """
    url = "http://d.web2.qq.com/channel/login2"
    method = WebQQRequest.METHOD_POST

    def init(self, relogin=False):
        self.relogin = relogin
        logger.info("准备完毕, 开始登录")
        self.headers.update(Referer=const.S_REFERER, Origin=const.D_ORIGIN)
        self.params = [("r", json.dumps({"status": "online",
                                         "ptwebqq": self.hub.ptwebqq,
                                         "passwd_sig": "",
                                         "clientid": self.hub.clientid,
                                         "psessionid": None})),
                       ("clientid", self.hub.clientid),
                       ("psessionid", "null")]

    def callback(self, resp, data):
        self.hub.require_check_time = None
        if not resp.body or not isinstance(data, dict):
            logger.error(u"没有获取到数据或数据格式错误, 登录失败:{0}"
                         .format(resp.body))
            self.hub.load_next_request(FirstRequest())
            return

        if data.get("retcode") != 0:
            logger.error("登录失败 {0!r}".format(data))
            self.hub.load_next_request(FirstRequest())
            return
        self.hub.vfwebqq = data.get("result", {}).get("vfwebqq")
        self.hub.psessionid = data.get("result", {}).get("psessionid")

        if not self.relogin:
            logger.info("登录成功, 开始加载好友列表")
            self.hub.load_next_request(FriendListRequest())
        else:
            logger.info("重新登录成功, 开始拉取消息")
            self.hub.start_poll()


class FriendListRequest(WebQQRequest):

    """ 加载好友信息
    """
    url = "http://s.web2.qq.com/api/get_user_friends2"
    method = WebQQRequest.METHOD_POST

    def init(self, first=True, manual=False):
        self.is_first = first
        self.manual = manual
        self.params = [("r", json.dumps({"h": "hello",
                                         "hash": self.hub._hash(),
                                         "vfwebqq": self.hub.vfwebqq}))]
        self.headers.update(Referer=const.S_REFERER)

    def callback(self, resp, data):
        if not resp.body and self.is_first:
            logger.error("加载好友信息失败, 重新开始登录")
            return self.hub.load_next_request(FirstRequest())
        if data.get("retcode") != 0 and self.is_first:
            logger.error("加载好友信息失败, 重新开始登录")
            return self.hub.load_next_request(FirstRequest())

        if isinstance(data, dict) and data.get("retcode") == 0:
            info = data.get("result", {})
            self.hub.set_friends(info)
            friends = self.hub.get_friends()
            logger.info(u"加载好友信息 {0!r}".format(friends))
            logger.debug(data)
            self.hub.load_next_request(FriendStatusRequest())
        else:
            logger.warn(u"加载好友列表失败: {0!r}".format(data))

        if not self.manual:
            self.hub.load_next_request(GroupListRequest())
            self.hub.load_next_request(DiscuListRequest())
            self.hub.load_next_request(FriendListRequest(delay=3600,
                                                         first=False))


FriendInfoRequest = FriendListRequest
import warnings
warnings.warn("In next version we will rename twqq.requests.FreindInfoRequest "
              "to twqq.requests.FriendListRequest")


class FriendStatusRequest(WebQQRequest):

    """ 获取在线好友状态
    """

    url = "https://d.web2.qq.com/channel/get_online_buddies2"

    def init(self):
        self.params = {"clientid": self.hub.clientid,
                       "psessionid": self.hub.psessionid,
                       "t": int(time.time() * 1000)}
        self.headers.update(Referer=const.D_REFERER)

    def callback(self, response, data):
        logger.info(u"加载好友状态信息: {0!r}".format(data))
        if isinstance(data, dict) and data.get("retcode") == 0:
            for item in data.get('result', []):
                self.hub.get_friends().set_status(**item)
        else:
            logger.warn(u"加载好友状态信息失败: {0!r}".format(data))


class GroupListRequest(WebQQRequest):

    """ 获取群列表
    """
    url = "http://s.web2.qq.com/api/get_group_name_list_mask2"
    method = WebQQRequest.METHOD_POST

    def init(self):
        self.params = {"r": json.dumps({"vfwebqq": self.hub.vfwebqq})}
        self.headers.update(Origin=const.S_ORIGIN)
        self.headers.update(Referer=const.S_REFERER)
        logger.info("获取群列表")

    def callback(self, resp, data):
        logger.debug(u"群信息 {0!r}".format(data))
        self.hub.set_groups(data.get("result", {}))
        groups = self.hub.get_groups()
        logger.info(u"群列表: {0!r}".format(groups))
        if not groups.gnamelist:
            self.hub.start_poll()

        for i, gcode in enumerate(groups.get_gcodes()):
            self.hub.load_next_request(GroupMembersRequest(gcode, i == 0))


class GroupMembersRequest(WebQQRequest):

    """ 获取群成员

    :param gcode: 群代码
    :param poll: 是否开始拉取信息和心跳
    :type poll: boolean
    """
    url = "http://s.web2.qq.com/api/get_group_info_ext2"

    def init(self, gcode, poll=False):
        self._poll = poll
        self._gcode = gcode
        self.params = [("gcode", gcode), ("vfwebqq", self.hub.vfwebqq),
                       ("cb", "undefined"), ("t", int(time.time() * 1000))]
        self.headers.update(Referer=const.S_REFERER)

    def callback(self, resp, data):
        if isinstance(data, dict) and data.get("retcode") == 0:
            logger.debug(u"获取群成员信息 {0!r}".format(data))
            members = data.get("result", {})
            groups = self.hub.get_groups()
            group = groups.find_group(self._gcode)
            group.set_group_detail(members)
            logger.debug(u"群详细信息: {0}".format(group))
        else:
            logger.warn(u"获取群成员信息失败 {0!r}".format(data))

        if self._poll:
            self.hub.start_poll()


class HeartbeatRequest(WebQQRequest):

    """ 心跳请求
    """
    url = "http://web.qq.com/web2/get_msg_tip"
    kwargs = dict(request_timeout=0.5, connect_timeout=0.5)

    def init(self):
        self.params = dict([("uin", ""), ("tp", 1), ("id", 0), ("retype", 1),
                            ("rc", self.hub.rc), ("lv", 3),
                            ("t", int(time.time() * 1000))])
        self.hub.rc += 1

    def callback(self, resp, data):
        logger.info("心跳...")


class PollMessageRequest(WebQQRequest):

    """ 拉取消息请求
    """
    url = "http://d.web2.qq.com/channel/poll2"
    method = WebQQRequest.METHOD_POST
    kwargs = {"request_timeout": 60.0, "connect_timeout": 60.0}

    def init(self):
        rdic = {"clientid": self.hub.clientid,
                "psessionid": self.hub.psessionid, "key": 0, "ids": []}
        self.params = [("r", json.dumps(rdic)),
                       ("clientid", self.hub.clientid),
                       ("psessionid", self.hub.psessionid)]
        self.headers.update(Referer=const.D_REFERER)
        self.headers.update(Origin=const.D_ORIGIN)
        self.ready = not self.hub.stop_poll

    def callback(self, resp, data):
        polled = False
        try:
            if not data:
                return

            if data.get("retcode") in [121, 120]:
                logger.error("获取登出消息, 尝试重新登录")
                self.hub.relogin()
                return

            logger.info(u"获取消息: {0!r}".format(data))
            self.hub.load_next_request(PollMessageRequest())
            polled = True
            self.hub.dispatch(data)
        except Exception as e:
            logger.error(u"消息获取异常: {0}".format(e), exc_info=True)
        finally:
            if not polled:
                self.hub.load_next_request(PollMessageRequest())


class SessGroupSigRequest(WebQQRequest):

    """ 获取临时消息群签名请求

    :param qid: 临时签名对应的qid(对应群的gid)
    :param to_uin: 临时消息接收人uin
    :param sess_reqeust: 发起临时消息的请求
    """

    url = "https://d.web2.qq.com/channel/get_c2cmsg_sig2"

    def init(self, qid, to_uin, sess_reqeust):
        self.sess_request = sess_reqeust
        self.to_uin = to_uin
        self.params = (("id", qid), ("to_uin", to_uin),
                       ("service_type", 0), ("clientid", self.hub.clientid),
                       ("psessionid", self.hub.psessionid), ("t", time.time()))
        self.headers.update(Referer=const.S_REFERER)

    def callback(self, resp, data):
        result = data.get("result")
        group_sig = result.get("value")
        if data.get("retcode") != 0:
            logger.warn(u"加载临时消息签名失败: {0}".format(group_sig))
            return

        logger.info(u"加载临时消息签名 {0} for {1}".format(group_sig, self.to_uin))
        self.hub.group_sig[self.to_uin] = group_sig
        self.sess_request.ready = True
        self.sess_request.init_params(group_sig)
        self.hub.load_next_request(self.sess_request)


class SessMsgRequest(WebQQRequest):

    """ 发送临时消息请求

    :param qid: 临时消息qid
    :param to_uin: 接收人 uin
    :param content: 发送内容
    """
    url = "https://d.web2.qq.com/channel/send_sess_msg2"
    method = WebQQRequest.METHOD_POST

    def init(self, qid, to_uin, content, style):
        self.to = to_uin
        self._content = content
        self.content = self.hub.make_msg_content(content, style)
        group_sig = self.hub.group_sig.get(to_uin)
        if not group_sig:
            self.ready = False
            self.hub.load_next_request(SessGroupSigRequest(qid, to_uin, self))
        else:
            self.init_params(group_sig)

    def init_params(self, group_sig):
        self.delay, self.number = self.hub.get_delay(self._content)
        self.params = (("r", json.dumps({"to": self.to, "group_sig": group_sig,
                                         "face": 549, "content": self.content,
                                         "msg_id": self.hub.msg_id,
                                         "service_type": 0,
                                         "clientid": self.hub.clientid,
                                         "psessionid": self.hub.psessionid})),
                       ("clientid", self.hub.clientid),
                       ("psessionid", self.hub.psessionid))

    def callback(self, resp, data):
        self.handle_retcode(data, u"[临时消息] {0} ==> {1}"
                            .format(self.content, self.to))
        self.hub.consume_delay(self.number)


class GroupMsgRequest(WebQQRequest):

    """ 发送群消息

    :param group_uin: 群uin
    :param content: 消息内容
    """
    url = "http://d.web2.qq.com/channel/send_qun_msg2"
    method = WebQQRequest.METHOD_POST

    def init(self, group_uin, content, style):
        self.delay, self.number = self.hub.get_delay(content)
        self.gid = self.hub.get_group_id(group_uin)
        self.group_uin = group_uin
        self.source = content
        content = self.hub.make_msg_content(content, style)
        r = {"group_uin": self.gid, "content": content,
             "msg_id": self.hub.msg_id, "clientid": self.hub.clientid,
             "psessionid": self.hub.psessionid}
        self.params = [("r", json.dumps(r)),
                       ("psessionid", self.hub.psessionid),
                       ("clientid", self.hub.clientid)]
        self.headers.update(Origin=const.D_ORIGIN, Referer=const.D_REFERER)

    def callback(self, resp, data):
        self.handle_retcode(data, u"[群消息] {0} ==> {1}"
                            .format(self.source, self.group_uin))
        self.hub.consume_delay(self.number)


class DiscuListRequest(WebQQRequest):
    """ 获取讨论组列表
    """
    url = "http://s.web2.qq.com/api/get_discus_list"

    def init(self):
        self.params = {"clientid": self.hub.clientid,
                       "psessionid": self.hub.psessionid,
                       "vfwebqq": self.hub.vfwebqq,
                       "t": time.time() * 1000}
        self.headers.update(Referer=const.S_REFERER)

    def callback(self, resp, data):
        logger.info(u"[群列表] ==> {0!r}".format(data))
        if data.get("retcode") == 0:
            self.hub.set_discu(data.get("result", {}))
            dids = self.hub.get_discu().dids
            for did in dids:
                self.hub.load_next_request(DiscuInfoRequest(did))


class DiscuInfoRequest(WebQQRequest):
    """ 获取讨论组详细信息

    :param did: 讨论组id
    """
    url = "https://d.web2.qq.com/channel/get_discu_info"

    def init(self, did):
        self.params = {"clientid": self.hub.clientid,
                       "did": did,
                       "psessionid": self.hub.psessionid,
                       "vfwebqq": self.hub.vfwebqq,
                       "t": time.time() * 1000}
        self.headers.update(Referer=const.S_REFERER)
        self._did = did

    def callback(self, resp, data):
        if data.get("retcode") == 0:
            discu = self.hub.get_discu()
            logger.info(u"[讨论组] ==> {0} 的详细信息: {1}"
                        .format(discu.get_name(self._did), data))
            discu.set_detail(self._did, data.get("result", {}))


class DiscuMsgRequest(WebQQRequest):
    """ 发送讨论组消息请求
    :param did: 讨论组id
    :param content: 消息内容
    """

    url = "https://d.web2.qq.com/channel/send_discu_msg2"
    method = WebQQRequest.METHOD_POST

    def init(self, did, content, style):
        self.delay, self.number = self.hub.get_delay(content)
        self.did = did
        self.source = content
        content = self.hub.make_msg_content(content, style)
        r = {"did": did, "content": content,
             "msg_id": self.hub.msg_id, "clientid": self.hub.clientid,
             "psessionid": self.hub.psessionid}
        self.params = [("r", json.dumps(r)),
                       ("psessionid", self.hub.psessionid),
                       ("clientid", self.hub.clientid)]
        self.headers.update(Referer=const.D_REFERER)

    def callback(self, resp, data):
        self.handle_retcode(data, u"[讨论组消息] {0} ==> {1}"
                            .format(self.source, self.did))
        self.hub.consume_delay(self.number)


class BuddyMsgRequest(WebQQRequest):

    """ 好友消息请求

    :param to_uin: 消息接收人
    :param content: 消息内容
    :param callback: 消息发送成功的回调
    """
    url = "http://d.web2.qq.com/channel/send_buddy_msg2"
    method = WebQQRequest.METHOD_POST

    def init(self, to_uin, content, style):
        self.to_uin = to_uin
        self.source = content
        self.content = self.hub.make_msg_content(content, style)
        r = {"to": to_uin, "face": 564, "content": self.content,
             "clientid": self.hub.clientid, "msg_id": self.hub.msg_id,
             "psessionid": self.hub.psessionid}
        self.params = [("r", json.dumps(r)), ("clientid", self.hub.clientid),
                       ("psessionid", self.hub.psessionid)]
        self.headers.update(Origin=const.D_ORIGIN)
        self.headers.update(Referer=const.S_REFERER)

        self.delay, self.number = self.hub.get_delay(content)

    def callback(self, resp, data):
        self.handle_retcode(data, u"[好友消息] {0} ==> {1}"
                            .format(self.source, self.to_uin))
        self.hub.consume_delay(self.number)


class SetSignatureRequest(WebQQRequest):

    """ 设置个性签名请求

    :param signature: 签名内容
    """
    url = "http://s.web2.qq.com/api/set_long_nick2"
    method = WebQQRequest.METHOD_POST

    def init(self, signature):
        self.params = (("r", json.dumps({"nlk": signature,
                                         "vfwebqq": self.hub.vfwebqq})),)
        self.headers.update(Origin=const.S_ORIGIN)
        self.headers.update(Referer=const.S_REFERER)

    def callback(self, resp, data):
        logger.info(u"[设置签名] {0}".format(data))


class AcceptVerifyRequest(WebQQRequest):

    """ 同意好友添加请求

    :param uin: 请求人uin
    :param qq_num: 请求人QQ号
    """
    url = "http://s.web2.qq.com/api/allow_and_add2"
    method = WebQQRequest.METHOD_POST

    def init(self, uin, qq_num, markname=""):
        self.uin = uin
        self.qq_num = qq_num
        self.markname = markname
        self.params = [("r", "{\"account\":%d, \"gid\":0, \"mname\":\"%s\","
                        " \"vfwebqq\":\"%s\"}" % (qq_num, markname,
                                                  self.hub.vfwebqq)), ]
        self.headers.update(Origin=const.S_ORIGIN)
        self.headers.update(Referer=const.S_REFERER)

    def callback(self, resp, data):
        if data.get("retcode") == 0:
            logger.info(u"[好友添加] 添加 {0} 成功".format(self.qq_num))
            # if self.markname:
            #     self.hub.mark_to_uin[self.markname] = self.uin
        else:
            logger.info(u"[好友添加] 添加 {0} 失败".format(self.qq_num))


class FileRequest(WebQQRequest):
    """ 下载传送的文件

    :param guid: 文件名
    :param lcid: 会话id
    :param to_uin: 发送人uin
    """
    url = "http://d.web2.qq.com/channel/get_file2"

    def init(self, guid, lcid, to, callback=None):
        self.params = {"clientid": self.hub.clientid,
                       "psessionid": self.hub.psessionid,
                       "count": 1, "time": int(time.time() * 1000),
                       "guid": guid, "lcid": lcid, "to": to}
        self.headers.update(Referer="http://web2.qq.com/webqq.html")
        self.headers.pop("Origin", None)
        self.fname = guid
        self._cb = callback

    def callback(self, response, data):
        """ 应该在客户端通过::

            @register_request_handler(FileRequest)
            def callback(resp, data):
                pass

        来实现文件的保存
        """
        if self._cb:
            self._cb(self.fname, response.body)


class LogoutRequset(WebQQRequest):
    """ 登出请求
    """
    url = "https://d.web2.qq.com/channel/logout2"

    def init(self):
        self.params = {"clientid": self.hub.clientid, "ids": "",
                       "psessionid": self.hub.psessionid,
                       "t": int(time.time() * 1000)}
        self.headers.update(Referer=const.D_REFERER)

    def callback(self, resp, data):
        if data.get("retcode") == 0:
            logger.info(u"登出成功")


FirstRequest = LoginSigRequest


def _register_message_handler(func, args_func, msg_type="message"):
    """ 注册成功消息器

    :param func: 处理器
    :param args_func: 产生参数的处理器
    :param mst_type: 处理消息的类型
    """
    func._twqq_msg_type = msg_type
    func._args_func = args_func
    return func


def group_message_handler(func):
    """ 装饰处理群消息的函数

    处理函数应接收5个参数:

        nickname        发送消息的群昵称
        content         消息内容
        group_code      群代码
        from_uin        发送人的uin
        source          消息原包
    """

    def args_func(self, message):
        value = message.get("value", {})
        gcode = value.get("group_code")
        uin = value.get("send_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(uin, contents, gcode)
        uname = self.get_group_member_nick(gcode, uin)
        return uname, content, gcode, uin, message

    return _register_message_handler(func, args_func, "group_message")


def buddy_message_handler(func):
    """ 装饰处理好友消息的函数

    处理函数应接收3个参数:

        from_uin         发送人uin
        content          消息内容
        source           消息原包
    """

    def args_func(self, message):
        value = message.get("value", {})
        from_uin = value.get("from_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(from_uin, contents)
        return from_uin, content, message
    return _register_message_handler(func, args_func, "message")


def kick_message_handler(func):
    """ 装饰处理下线消息的函数

    处理函数应接收1个参数:

        source      消息原包
    """

    def args_func(self, message):
        return message,
    return _register_message_handler(func, args_func, "kick_message")


def sess_message_handler(func):
    """ 装饰处理临时消息的函数

    处理函数应接收3个参数:

        id              获取组签名的id
        from_uin        发送人uin
        content         消息内容
        source          消息原包
    """

    def args_func(self, message):
        value = message.get("value", {})
        id_ = value.get("id")
        from_uin = value.get("from_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(from_uin, contents)
        return id_, from_uin, content, message

    return _register_message_handler(func, args_func, "sess_message")


def system_message_handler(func):
    """ 装饰处理系统消息的函数

    处理函数应接手4个参数:

        type        消息类型
        from_uin    产生消息的人的uin
        account     产生消息的人的qq号
        source      消息原包
    """

    def args_func(self, message):
        value = message.get('value')
        return (value.get("type"), value.get("from_uin"), value.get("account"),
                message)
    return _register_message_handler(func, args_func, "system_message")


def discu_message_handler(func):
    """ 装饰处理讨论组消息的函数

    处理函数应接收
        did        讨论组id
        from_uin   发送消息的人
        content    消息内容
        source     消息原包
    """

    def args_func(self, message):
        value = message.get("value")
        from_uin = value.get("send_uin")
        did = value.get("did")
        content = self.handle_qq_msg_contents(
            from_uin, value.get("content", []), did, 1)
        return (did, from_uin, content, message)

    return _register_message_handler(func, args_func, "discu_message")


def file_message_handler(func):
    """ 装饰处理文件消息的函数

    处理函数应接受
        from_uin        文件发送人
        to_uin          文件接收人
        lcid            文件sessionid (此处为 session_id 字段)
        guid            文件名称 (此处为 name 字段)
        is_cancel       是否是取消发送
        source          消息源包
    """
    def args_func(self, message):
        value = message.get("value", {})
        return (value.get("from_uin"), value.get("to_uin"),
                value.get("session_id"), value.get("name"),
                value.get("cancel_type", None) == 1,
                message)
    return _register_message_handler(func, args_func, "file_message")


def offline_file_message_handler(func):
    """ 装饰处理离线文件的函数

    处理函数应接收
        from_uin        文件发送人
        to_uin          文件接收人
        lcid            文件sessionid (此处为 session_id 字段)
        count           离线文件数量
        file_infos      文件信息
        source          消息源包
    """
    warnings.warn(u"WebQQ的离线消息并不可靠, 对方可能发送, 但是收不到")

    def args_func(self, message):
        value = message.get("value", {})
        return (value.get("from_uin"), value.get("to_uin"),
                value.get("lcid"), value.get("count"),
                value.get("file_infos"), message)

    return _register_message_handler(func, args_func, "filesrv_transfer")


def check_request(request):
    """ 检查Request参数是否合法, 并返回一个类对象
    """
    if inspect.isclass(request):
        if not issubclass(request, WebQQRequest):
            raise ValueError("Request must be a subclass of WebQQRequest")
    elif isinstance(request, WebQQRequest):
        request = request.__class__
    else:
        raise ValueError(
            "Request must be a subclass or instance of WebQQRequest")

    return request


def register_request_handler(request):
    """ 返回一个装饰器, 用于装饰函数,注册为Request的处理函数
    处理函数需接收两个参数:

        request         本次请求的实例
        response        相应 ~tornado.httpclient.HTTPResponse instance
        data            response.body or dict

    :param request: 请求类或请求实例
    :type request: WebQQRequest or WebQQRequest instance
    :rtype: decorator function
    """
    def wrap(func):
        func._twqq_request = check_request(request)
        return func
    return wrap
