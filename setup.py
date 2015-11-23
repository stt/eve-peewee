#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup
import os

DESCRIPTION = ("Data layer for Eve powered by peewee.")

cwd = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(cwd, 'README.md')

try:
    with open(readme_path) as f:
        LONG_DESCRIPTION = f.read()
except (OSError, IOError) as e:
    LONG_DESCRIPTION = ""

install_requires = [
    'Eve>=0.5',
    'peewee>=2.6',
]

setup(
    name='eve-peewee',
    version='0.0.2',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Samuli Tuomola',
    author_email='samuli.tuomola@gmail.com',
    url='https://github.com/stt/eve-peewee',
    license='BSD',
    platforms=["any"],
    packages=['eve_peewee'],
    test_suite="eve_peewee.tests",
    install_requires=install_requires,
    extras_require={
        'test': [
            'pytest',
            'mock',
            ]
        },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
