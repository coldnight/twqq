#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/04/11 17:28:15
#   Desc    :   将返回信息实例化
#
""" 对应WebQQ的数据结构抽象
"""
import logging

logger = logging.getLogger("twqq")


class UniqueIds(object):
    """ 唯一ID
    为每个好友/群/讨论组/群成员都保持一个唯一标识
    """
    T_FRI = 1   # 好友
    T_TMP = 0   # 临时(群成员)
    T_GRP = 4   # 群
    T_DIS = 3   # 讨论组

    _map = {}     # 分配的id 到 uin和type的对应关系
    _r_map = {}   # uin 和 id 的对应关系
    _last_id = 0  # 最后一个id, 保持唯一

    @classmethod
    def alloc(cls, uin, _type):
        """ 分配一个, uin 是webqq的唯一标识, _type 对应 组/好友/讨论组/群成员
        并返回这个 id
        """
        assert _type in [cls.T_FRI, cls.T_TMP, cls.T_GRP, cls.T_DIS]
        if uin in cls._r_map:
            return cls._r_map[uin]
        else:
            _id = cls._last_id
            cls._last_id += 1
            cls._map[_id] = (uin, _type)
            cls._r_map[uin] = _id
            return _id

    @classmethod
    def get(cls, _id):
        """ 根据 _id 获取 uin 和对应的类型
        """
        return cls._map.get(_id, (None, None))

    @classmethod
    def get_type(cls, uin):
        """ 根据 uin 判断该uin 的类型
        """
        return cls._map.get(cls._r_map.get(uin), (None, None))[1]

    @classmethod
    def get_id(cls, uin):
        return cls._r_map.get(uin)


class ObjectsBase(object):

    def __init__(self, **kw):
        for key, val in kw.items():
            setattr(self, key, val)


class GroupMInfo(ObjectsBase):

    """ 对应群成员信息中的 minfo 字段中的元素

    :param nick: 成员qq昵称
    :param province: 成员省份
    :param gender: 成员性别
    :param uin: uin
    :param contry: 国家
    :param city: 城市
    :param client_type: 客户端类型
    :param stat: 目测固定都给10
    :param mflag: 1 则是管理员, 0 是普通成员
    :param card: 群名片
    """

    def __init__(self, nick, province, gender, uin, country, city,
                 stat=None, client_type=None, mflag=None, card=None):
        self.nick = nick
        self.province = province
        self.gender = gender   # 性别
        self.uin = uin
        self.country = country
        self.city = city

        self.stat = stat
        self.client_type = client_type
        self.card = card
        self._id = UniqueIds.alloc(uin, UniqueIds.T_TMP)

    def is_manager(self):
        return True if self.mflag == 1 else False


class VipInfo(ObjectsBase):

    """ 对应群信息 vipinfo 字段

    :param vip_level: 会员等级
    :param u: 用户 uin
    :param is_vip: 是否是管理员
    """

    def __init__(self, vip_level, u, is_vip):
        self.vip_level = vip_level
        self.u = u
        self.is_vip = True if is_vip == 1 else False


class Group(ObjectsBase):
    def __init__(self, flag, name, gid, code, memo=None, fingermemo=None,
                 createtime=None, level=None, owner=None, option=None,
                 members=None):
        self.flag = flag
        self.name = name
        self.gid = gid
        self.code = code
        self.group = None

        self.memo = memo
        self.fingermemo = fingermemo
        self.createtime = createtime
        self.level = level
        self.owner = owner
        self.option = option
        self._uin_map = {}   # 群成员 uin 映射
        self._uin_name_map = {}  # 群成员昵称到uin的映射
        self._id = UniqueIds.alloc(code, UniqueIds.T_GRP)

    def update(self, **kw):
        for key, val in kw.items():
            setattr(self, key, val)

    def set_group_detail(self, data):
        """ 设置组详细信息, 包括群成员信息, 等.
        """
        for kw in data.get("minfo", []):
            nick, uin = kw.get("nick"), kw.get("uin")
            if nick is not None:
                tmp = GroupMInfo(**kw)
                self._uin_name_map[tmp.nick] = tmp.uin
                self._uin_map[tmp.uin] = tmp

        for item in data.get("cards", []):
            uin = item.get("muin")
            if uin in self._uin_map and item.get("card") is not None:
                self._uin_map[uin].card = item.get("card")
                self._uin_name_map[item.get("card")] = uin
            else:
                logger.warn(u"card info {0} not in map: {1!r}"
                            .format(uin, item))

        for item in data.get("stats", []):
            uin = item.get("uin")
            if uin in self._uin_map:
                self._uin_map[uin].stat = item.get("stat")
                self._uin_map[uin].client_type = item.get("client_type")
            else:
                logger.warn(u"stats info {0} not in map: {1!r}"
                            .format(uin, item))

        for item in data.get("vipinfo", []):
            u = item.get("u")
            if u in self._uin_map:
                self._uin_map[u].vipinfo = item
            else:
                logger.warn(u"vip info {0} not in map: {1!r}"
                            .format(uin, item))

        self.set_detail_info(**data.get("ginfo", {}))

    def __iter__(self):
        """ 迭代返回成员的 uin
        """
        if hasattr(dict, "iterkeys"):
            return self._uin_map.iterkeys()
        else:
            return self._uin_map.keys()

    def set_detail_info(self, face, memo, fingermemo, code, createtime,
                        flag, level, name, gid, owner, option, members, **kw):
        """ 组成员信息中对应 ginfo 中的元素

        :param face: 群头像
        :param memo:
        :param class: 群类型
        :param fingermemo:
        :param createtime: 创建时间戳
        :param flag:
        :param level:
        :param name: 群名称
        :param gid: 群hash码
        :param owner: 群主 uin
        :param option:
        :param members: 群成员
        """
        self.face = face
        self.memo = memo
        self._class = kw["class"]
        self.fingermemo = self.fingermemo
        self.createtime = createtime
        self.flag = flag
        self.level = level
        self.name = name
        self.gid = gid
        self.owner = owner
        self.option = option

        for item in members:
            uin = item.get("muin")
            tmp = self._uin_map.get(uin)
            if tmp:
                tmp.mflag = item.get("mflag")

    def __repr__(self):
        return u"<Group {0} have {1} members, Level {2}>"\
            .format(self.name, len(self._uin_map.keys()), self.level)

    def __unicode__(self):
        return self.__repr__()

    def get_nickname(self, uin):
        """ 获取群成员的昵称
        """
        r = self._uin_map.get(uin)
        if r:
            return r.nick

    def get_cardname(self, uin):
        """ 获取群成员群名片
        """
        r = self._uin_map.get(uin)
        if r:
            return r.card

    def get_show_name(self, uin):
        """ 获取显示名, 群名片优先, 无则取昵称
        """
        r = self._uin_map.get(uin)
        if r:
            return r.card if r.card else r.nick

    def get_member_info(self, uin):
        return self._uin_map.get(uin)

    def is_manager(self, uin):
        """ 判断用户是否是群管理员
        """
        r = self._uin_map.get(uin)
        if r:
            return r.is_manager()


class GroupList(ObjectsBase):
    """ 组列表抽象
    """

    def __init__(self, data):
        self._gcode_map = {}
        self._gid_gcode_map = {}
        self._gcode_name_map = {}
        self.update(data)

    def update(self, data):
        for kw in data.get("gnamelist", []):
            gcode = kw.get("code")
            if gcode not in self._gcode_map:
                group = Group(**kw)
                self._gcode_map[gcode] = group
                self._gid_gcode_map[kw.get("gid")] = gcode
                self._gcode_name_map[kw.get("name")] = gcode
            else:
                self._gcode_map[gcode].update(**kw)
        self.gmasklist = data.get("gmasklist", [])
        self.gmarklist = data.get("gmarklist", [])

    @property
    def gnamelist(self):
        return self._gcode_map.values()

    def __repr__(self):
        return str([x.name for x in self._gcode_map.values()])

    def __unicode__(self):
        return self.__repr__().decode("utf-8")

    def __iter__(self):
        """ 迭代返回群对象
        """
        if hasattr(dict, "itervalues"):
            return self._gcode_map.itervalues()
        else:
            return self._gcode_map.values()

    @property
    def groups(self):
        return [x for x in self._gcode_map.values()]

    def get_gcodes(self):
        return [x.code for x in self._gcode_map.values()]

    def find_group(self, gcode):
        return self._gcode_map.get(gcode)

    def set_group_info(self, gcode, data):
        """ 设置群信息

        :param gcode: 组代码
        :param data: 数据
        """
        item = self.find_group(gcode)
        if item:
            item.set_group_detail(data)

    def get_members(self, gcode):
        """  获取指定组的成员信息
        """
        item = self.find_group(gcode)
        if item:
            return item._uin_map.values()

    def get_member(self, gcode, uin):
        """ 获取指定群成员的信息
        """
        item = self.find_group(gcode)
        if item:
            return item.get_member(uin)

    def get_group_name(self, gcode):
        item = self.find_group(gcode)
        if item:
            return item.name

    def get_member_nick(self, gcode, uin):
        item = self.find_group(gcode)
        if item:
            return item.get_show_name(uin)

    def get_gid(self, gcode):
        item = self.find_group(gcode)
        if item:
            return item.gid

    def get_gcode(self, gid):
        return self._gid_gcode_map.get(gid)


class DiscuMemInfo(ObjectsBase):

    """ 讨论组成员信息

    :param uin: uin
    :param nick: 昵称
    """

    def __init__(self, uin, nick, status=None, client_type=None):
        self.uin = uin
        self.nick = nick
        self.status = status
        self.client_type = client_type
        self._id = UniqueIds.alloc(uin, UniqueIds.T_TMP)


class Discu(ObjectsBase):

    """ 讨论组信息抽象

    :param did: 讨论组id
    :param name: 讨论组名称
    """

    def __init__(self, did, name, discu_owner=None, discu_name=None,
                 info_seq=None, mem_list=None):
        self._uin_map = {}
        self.did = did
        self.name = name
        self.discu_name = discu_name,
        self.discu_owner = discu_owner
        self.info_seq = info_seq
        self.mem_list = mem_list
        self._id = UniqueIds.alloc(did, UniqueIds.T_DIS)

    def set_detail(self, info, mem_status, mem_info):
        self.discu_name = info.get("discu_name")
        self.discu_owner = info.get("discu_owner")
        self.info_seq = info.get("info_seq")
        for item in mem_info:
            self._uin_map[item["uin"]] = DiscuMemInfo(**item)

        for item in mem_status:
            tmp = self._uin_map.get(item["uin"])
            if tmp:
                tmp.status = item.get("status")
                tmp.client_type = item.get("client_type")

    def get_mname(self, uin):
        item = self._uin_map.get(uin)
        if item:
            return item.nick


class DiscuList(ObjectsBase):

    """ 讨论组列表
    """

    def __init__(self, data):
        self._did_map = {}
        self._did_name_map = {}

        self.update(data)

    def update(self, data):
        for item in data.get("dnamelist"):
            did = item["did"]
            if did not in self._did_map:
                self._did_name_map[item["name"]] = item["did"]
                self._did_map[did] = Discu(item["did"], item["name"])
            else:
                self._did_map[did].did = did
                self._did_map[did].name = item["name"]

    @property
    def dids(self):
        return self._did_map.keys()

    @property
    def discus(self):
        return [x for x in self._did_map.values()]

    def get_name(self, did):
        r = self._did_map.get(did)
        if r:
            return r.name

    def set_detail(self, did, data):
        self._did_map[did].set_detail(**data)

    def get_did(self, name):
        return self._did_name_map.get(name)

    def get_mname(self, did, uin):
        r = self._did_map.get(did)
        if r:
            return r.get_mname(uin)


class FriendInfo(ObjectsBase):

    """ 好友信息抽象

    :param uin: 唯一标识
    :param face: 头像
    :param nick: 昵称
    :param birthday: 生日
    :param occpation:
    :param phone: 手机号
    :param allow:
    :param colleage: 大学
    :param uin: uin
    :param constel:
    :param blood: 血型
    :param homepage: 主页
    :param stat: 状态
    :param vip_info: 是否vip
    :param country: 国家
    :param city: 城市
    :param personal:
    :param shengxiao: 生肖
    :param email: 邮件
    :param client_type: 客户端类型
    :param province: 省份
    :param gender: 性别
    :param mobile: 手机
    :param markname: 备注名
    :param categories: 分类id
    :param account: QQ号
    """
    def __init__(self, uin, face, flag, nick, birthday=None,
                 occpation=None, phone=None, allow=None, colleage=None,
                 constel=None, blood=None, homepage=None, status=None,
                 vip_info=None, country=None, city=None, personal=None,
                 shengxiao=None, email=None, client_type=None, province=None,
                 gender=None, mobile=None, markname=None, categories=None,
                 account=None):
        self.face = face
        self.flag = flag
        self.nick = nick
        self.uin = uin
        self.birthda = birthday
        self.occpation = occpation
        self.phone = phone
        self.allow = allow
        self.colleage = colleage
        self.constel = constel
        self.blood = blood
        self.homepage = homepage
        self.status = status
        self.vip_info = vip_info
        self.country = country
        self.city = city
        self.personal = personal
        self.shengxiao = shengxiao
        self.email = email
        self.client_type = client_type
        self.province = province
        self.gender = gender
        self.mobile = mobile
        self.markname = markname
        self.categories = categories
        self.account = account
        self._id = UniqueIds.alloc(uin, UniqueIds.T_FRI)

    def update(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    def set_markname(self, markname):
        self.markname = markname

    def set_categories(self, categories):
        self.categories = categories

    def set_vipinfo(self, vipinfo):
        self.vip_info = vipinfo

    def set_detail(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FriendCate(ObjectsBase):

    """ 好友分类

    :param index: 索引
    :param sort: 排序
    :param name: 名称
    """
    def __repr__(self):
        return u"<Category [{0}]>".format(self.name)


class Friends(ObjectsBase):

    def __init__(self, data):
        self._uin_map = {}
        self._name_map = {}
        self._mark_uin_map = {}
        self.update(data)

    def update(self, data):
        for item in data.get("info", {}):
            uin = item["uin"]
            if uin not in self._uin_map:
                info = FriendInfo(**item)
                self._uin_map[info.uin] = info
                self._name_map[info.nick] = info.uin
            else:
                self._uin_map[uin].update(**item)

        for item in data.get("friends", []):
            uin = item.get("uin")
            self._uin_map[uin].set_categories(item.get("categories"))

        for item in data.get("marknames", []):
            uin = item.get("uin")
            self._uin_map[uin].set_markname(item.get("markname"))
            self._mark_uin_map[item.get("markname")] = uin

        for item in data.get("vipinfo", []):
            uin = item.get("u")
            self._uin_map[uin].set_vipinfo(item)
        self.categories = [FriendCate(**kw)
                           for kw in data.get("categories", [])]
        self.vipinfo = [VipInfo(**kw) for kw in data.get("vipinfo", [])]

    def get_uin(self, name):
        return self._name_map.get(name)

    @property
    def info(self):
        return [self._uin_map[uin] for uin in self._uin_map]

    def __repr__(self):
        return u"<{0} Friends>".format(len(self.info))

    def get_nick(self, uin):
        """ 获取好友信息昵称
        """
        item = self._uin_map.get(uin)
        if item:
            return item.nick

    def get_markname(self, uin):
        """ 获取好友备注信息
        """
        item = self._uin_map.get(uin)
        if item:
            return item.markname

    def get_show_name(self, uin):
        m = self.get_markname(uin)
        if not m:
            m = self.get_nick(uin)
        return m

    def get_uin_from_mark(self, mark):
        return self._mark_uin_map.get(mark)

    def set_status(self, uin, status, client_type):
        item = self._uin_map.get(uin)
        if item:
            item.status = status
            item.client_type = client_type

    def set_account(self, uin, account):
        item = self._uin_map.get(uin)
        if item:
            item.account = account

    def get_account(self, uin):
        item = self._uin_map.get(uin)
        if item:
            return item.account
