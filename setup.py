#!/usr/bin/env python

from setuptools import setup
DESCRIPTION = ("Data layer for Eve powered by peewee.")

with open('README.md') as f:
    LONG_DESCRIPTION = f.read()

#with open('CHANGES') as f:
#    LONG_DESCRIPTION += f.read()

install_requires = [
    'Eve>=0.5',
    'peewee>=2.7',
]

setup(
    name='eve-peewee',
    version=__import__('eve_peewee').__version__,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Samuli Tuomola',
    author_email='samuli.tuomola@gmail.com',
    url='https://github.com/stt/eve-peewee',
    license='BSD',
    platforms=["any"],
    packages=['eve_peewee'],
    #test_suite="eve_peewee.tests",
    #install_requires=install_requires,
    extras_require={
        'tests': [
            'pytest',
            'mock',
            'pytest-flakes',
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
