#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup
import os

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()

setup(
    name='eve-peewee',
    version='0.0.6',
    description="Data layer for Eve powered by peewee.",
    long_description=long_description,
    author='Samuli Tuomola',
    author_email='samuli.tuomola@gmail.com',
    url='https://github.com/stt/eve-peewee',
    license='BSD',
    platforms=["any"],
    packages=['eve_peewee'],
    test_suite="eve_peewee.tests",
    install_requires=['Eve>=0.6','peewee>=2.8'],
    setup_requires=['pytest'],
    extras_require={
        'test': []
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
