#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/09/05 11:16:58
#   Desc    :
#
import twqq
from setuptools import setup

requires = ["tornado", "pycurl", "tornadohttpclient"]

packages = ["twqq"]

entry_points = {
}


setup(
    name = "twqq",
    version = twqq.__version__,
    description = 'An asynchronous webqq client library based on tornado',
    long_description = open("README.rst").read(),
    author = 'cold',
    author_email = 'wh_linux@126.com',
    url = 'http://www.linuxzen.com',
    license = 'Apache 2.0',
    platforms = 'any',
    packages = packages,
    package_data = {
    },
    entry_points = entry_points,
    install_requires = requires,
    classifiers=['Development Status :: 3 - Alpha',
                 'Environment :: Console',
                 "Intended Audience :: Developers",
                 'License :: OSI Approved :: Apache Software License',
                 'Topic :: Internet :: WWW/HTTP',
                 'Programming Language :: Python :: 2.7',
                 ],
)
