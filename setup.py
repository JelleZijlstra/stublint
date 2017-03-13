#!/usr/bin/env python
# coding: utf-8

import sys
from distutils.core import setup

if sys.version_info < (3, 6):
    sys.stderr.write('ERROR: You need Python 3.6 to run stublint.\n')
    sys.exit(1)

classifiers = [
    'Development Status :: 2 - Pre-Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3.6',
    'Topic :: Software Development',
]

setup(name='stublint',
      version='0.0',
      description='Linter for pyi files, inteded for use in typeshed',
      author='Jelle Zijlstra',
      author_email='jelle.zijlstra@gmail.com',
      url='https://www.github.com/JelleZijlstra/stublint',
      license='PSF',
      keywords='typing function annotations type hints hinting checking '
               'checker typehints typehinting typechecking lint',
      py_modules=['stublint'],
      classifiers=classifiers)
