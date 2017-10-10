#!/usr/bin/env python

from setuptools import setup

setup(
name="smartfeed",
version="1.0.0",
description="Fanout Smart Feed",
author="Justin Karneges",
author_email="justin@fanout.io",
url="https://github.com/fanout/pysmartfeed",
license="MIT",
packages=['smartfeed', 'smartfeed.django', 'smartfeed.django.app'],
install_requires=["pubcontrol>=2.4.2,<3", "gripcontrol>=3.0.2,<4"],
classifiers=[
	"Topic :: Utilities",
	"License :: OSI Approved :: MIT License"
]
)
