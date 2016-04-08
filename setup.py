#!/usr/bin/python
##############################################################################
#
# Copyright (c) 2006-2015 Agendaless Consulting and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE
#
##############################################################################

import os
import sys

from setuptools import setup, find_packages

requires = [
    "pyyaml",
    "pytimeparse",
    "docker-py",
]
tests_require = [
    "coverage",
]
testing_extras = []

here = os.path.abspath(os.path.dirname(__file__))
README = ''
CHANGES = ''
try:
    README = open(os.path.join(here, 'README.rst')).read()
except:
    try :
        for line_no, line in enumerate(open(os.path.join(here, 'README.md'))) :
            if line_no==1 :
                README = line.strip()
    except :
        pass
try:
    CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()
except:
    pass

CLASSIFIERS = [
    'Development Status :: 1 - Beta',
    'Environment :: Console',
    'Natural Language :: English',
    'Operating System :: POSIX',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
]

class ChangeDir(object) : 
    def __init__(self, wd) : 
        self.wd = wd
    def __enter__(self):
        self._pwd = os.getcwd()
        if self.wd :
            os.chdir(self.wd)
    def __exit__(self, *args, **kwds) : 
        os.chdir(self._pwd)

def getDirtyState() :
    import subprocess
    p = subprocess.Popen(['git', 'status', '-s', '--untracked-files=no'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0 :
        raise RuntimeError('Failed to retrieve clean/dirty status, stdout:\n%s\nstderr:\n%s'%(stdout, stderr))
    if stdout :
        return "-dirty"
    else :
        return ""

def getVersion() :
    with ChangeDir(os.path.dirname(__file__)) :
        version = None
        if os.path.exists('.git') :
            import subprocess
            p = subprocess.Popen(['git', 'describe'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode == 0 :
                version = stdout.strip()
                if version[0] == 'v' :
                    version = version[1:]
                import re
                match = re.match("([^-]*)(?:-([^-])-([^-]*)|)", version)
                if match :
                    version, changes, commit = match.groups()
                    if changes :
                        version = "%s.dev%s"%(version, changes)
                    version += getDirtyState()
        elif os.path.exists("PKG-INFO") :
            import re
            versionRe = re.compile("Version:[\s]*([^\s]*).*")
            for line in file("PKG-INFO") :
                match = versionRe.match(line)
                if match :
                    version = match.group(1)
        if not version :
            version = "0.0.0"
        return version

dist = setup(
    name='caduc',
    version=getVersion(),
    license='GNU GPLv3',
    url='https://github.com/tjamet/caduc',
    description='caduc monitors docker events and schedules clean-up when resources are nor used any longer',
    long_description=README + '\n\n' + CHANGES,
    classifiers=CLASSIFIERS,
    author="Thibault Jamet",
    author_email=''.join([chr(i) for i in [116, 104, 105, 98, 97, 117, 108, 116, 46, 106, 97, 109, 101, 116, 64, 103, 109, 97, 105, 108, 46, 99, 111, 109]]),
    maintainer="Thibault Jamet",
    maintainer_email=''.join([chr(i) for i in [116, 104, 105, 98, 97, 117, 108, 116, 46, 106, 97, 109, 101, 116, 64, 103, 109, 97, 105, 108, 46, 99, 111, 109]]),
    packages=find_packages(),
    install_requires=requires,
    extras_require={
        'testing': testing_extras,
        },
    tests_require=tests_require,
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'caduc = caduc.cmd:main',
        ],
    },
)
