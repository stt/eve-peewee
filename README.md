Eve Peewee extension
====================

[![Build Status](https://travis-ci.org/stt/eve-peewee.svg)](https://travis-ci.org/stt/eve-peewee)

This is a WIP data layer for [Eve](http://python-eve.org/) using [peewee](http://peewee-orm.com/)

Currently peewee creates tables based on settings.py DOMAIN declarations during start-up and basic Eve CRUD methods work.

#### Instuctions

* python setup.py install
* define DATABASE_URI in settings.py (see examples)
* Eve(data=EvePeewee).run()

#### Notable caveats

* only postgres supported atm
* peewee doesn't do auto-migration (if you change domain models, drop the tables to get them recreated or apply changes in db manually)
* peewee specific field properties can be defined in DOMAIN schema (requires "transparent_schema_rules"), e.g. `'_peewee': { 'primary_key': True }`
* objectid and media types are unsupported (list and dict types are saved as jsonb)
* many of the mongo centric field properties (anyof, allof etc) are silently ignored
* only python 2.7 tested (unit tests coming)
* fancy stuff, like data relationships (fkey), validations etc, not yet tested

