import peewee
from playhouse import db_url

import eve
from eve.utils import config
from eve.io.base import DataLayer, BaseJSONEncoder
from werkzeug.exceptions import HTTPException, abort
from cerberus import Validator

from datetime import datetime
import time, json, ast, operator
import traceback, sys

__version__ = '0.0.3'

import logging
logger = logging.getLogger(__name__)


class BaseModel(peewee.Model):
    _created = peewee.DateTimeField()
    _updated = peewee.DateTimeField()
    _deleted = peewee.BooleanField({'required':True})

    def __contains__(self, key):
        return key in self._data


class PeeweeJSONEncoder(BaseJSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return str(obj)
        else:
            return super(PeeweeJSONEncoder, self).default(obj)


class EvePeeweeResultIterator(object):
    def __init__(self, qrw):
        self.qrw = qrw
        self._idx = 0

    def next(self):
        if self._idx < self.qrw._ct:
            obj = self.qrw._result_cache[self._idx]
        elif not self.qrw._populated:
            obj = self.qrw.iterate()
            self.qrw._result_cache.append(obj)
            self.qrw._ct += 1
        else:
            raise StopIteration
        self._idx += 1
        return obj._data
    __next__ = next


class EvePeeweeResultWrapper(peewee.NaiveQueryResultWrapper):
    def count(self, **kwargs):
        if hasattr(self, '_count'):
            return self._count
        else:
            return super(EvePeeweeResultWrapper, self).count

    def __iter__(self):
        if self._populated:
            return iter(self._result_cache)
        else:
            return EvePeeweeResultIterator(self)


def validate_filters(where, resource):
    allowed = config.DOMAIN[resource]['allowed_filters']
    if '*' in allowed or not config.VALIDATE_FILTERS:
        return None

    for key, value in where.items():
        if key not in allowed:
            return "filter on '%s' not allowed" % key

        res_schema = config.DOMAIN[resource]['schema']
        if key not in res_schema:
            return "filter on '%s' is invalid" % key
        else:
            field_schema = res_schema.get(key)
            v = Validator({key: field_schema})
            if not v.validate({key: value}):
                return "filter on '%s' is invalid" % key
            else:
                return None


class EvePeewee(DataLayer):
    json_encoder_class = PeeweeJSONEncoder

    _eve_peewee_field_map = {
        'string': peewee.TextField,
        'boolean': peewee.BooleanField,
        'integer': peewee.IntegerField,
        'float': peewee.FloatField,
        'number': peewee.FloatField,
        'datetime': peewee.DateTimeField
    }

    def _get_model_cls(self, resource):
        try:
            return self.models[resource]
        except KeyError:
            abort(404)

    def _doc_to_model(self, resource, doc):
        cls = self._get_model_cls(resource)
        # TODO: custom Validator
        for field_name,fs in config.DOMAIN[resource]['schema'].items():
          # if m:m then validate that all elements are ints
          if 'data_relation' in fs and fs['type'] == 'list':
            for f in doc[field_name]:
              if not isinstance(f, int):
                abort(400, "value '%s' cannot be converted to int" % f)
        instance = cls(**doc)
        return instance

    def _handle_exception(self, exc):
        if self.app.debug:
            raise exc
        else:
            self.app.logger.exception(exc)
            abort(400, description=str(exc))

    def _parse_where(self, op, where):
        try:
            query,joins = op.convert_dict_to_node(where)
            return op.filter(reduce(operator.and_, query))
        except AttributeError as exc:
            self.app.logger.warn("missing field?")
            self._handle_exception(exc)

    def _get_fieldtype(self, name):
        fld = None
        if name in self._eve_peewee_field_map:
            fld = self._eve_peewee_field_map[name]
        elif name == 'dict' or name == 'list':
            # TODO: db agnostic
            from playhouse.postgres_ext import BinaryJSONField
            fld = BinaryJSONField
        return fld
 
    def init_app(self, app):
        # eve.utils.config is not yet setup so use app.config here
        if 'DATABASE_URI' in app.config:
            if app.config['DATABASE_URI'].startswith('postgres'):
                url = db_url.parse(app.config['DATABASE_URI'])
                from playhouse.postgres_ext import PostgresqlExtDatabase
                self.driver = PostgresqlExtDatabase(register_hstore=False, **url)
            else:
                self.driver = db_url.connect(app.config['DATABASE_URI'])

        # http://python-eve.org/config.html#schema
        # http://docs.peewee-orm.com/en/latest/peewee/models.html#fields
        # TODO min/max_length could be supported in python but not by peewee
        # http://docs.peewee-orm.com/en/latest/peewee/models.html#some-fields-take-special-parameters

        # mapping from eve field schema properties to peewee properties
        pw_eve_fld_prop_map = {
            'default': 'default', 'unique': 'unique', 
        }
        # list of peewee specific properties that can be set for under eve
        # field schema using special dict named '_peewee'
        pw_fld_props = ['primary_key','index']

        self.models = {}
        self.link_tables = {}

        class Meta:
            database = self.driver

        # HACK to workaround eve.utils.auto_fields
        #eve.utils.Config.__getattr__ = lambda s,key: app.config[key]

        for res_name, v in app.config['DOMAIN'].items():
            if 'schema' not in v: continue
            base = {'Meta':Meta}

            primary_key_set = False

            for field_name,fs in v['schema'].items():
                # initial arguments for peewee field creation
                args = {pw_eve_fld_prop_map[k]: fs[k] for k in fs.keys() if k in pw_eve_fld_prop_map}
                #args.update({k:fs[k] for k in fs.keys() if k in pw_fld_props})

                if '_peewee' in fs:
                    args.update(fs['_peewee'])

                if 'required' not in fs:
                    args['null'] = True
                else:
                    args['null'] = not fs['required']

                if 'data_relation' in fs and fs['data_relation']:
                    continue
                elif 'primary_key' in fs and fs['primary_key']:
                    fld = peewee.PrimaryKeyField(**args)
                    primary_key_set = True
                # unsupported: objectid, media, geojson
                else:
                    fld = self._get_fieldtype(fs['type'])
                    if not fld:
                        raise TypeError("unknown: " + fs['type'])
                    fld = fld(**args)

                base[field_name] = fld

            if not primary_key_set:
                # eve's default ID_FIELD is _id, peewee's is id
                base[app.config['ID_FIELD']] = peewee.PrimaryKeyField()

            #app._set_resource_defaults(res_name, app.config['DOMAIN'][res_name])
            #print eve.utils.auto_fields(res_name)
            #print self._datasource_ex(res_name)
            mod = type(res_name, (BaseModel,), base)

            self.models[res_name] = mod

        # second pass for foreign keys
        for res_name, v in app.config['DOMAIN'].items():
            for field_name,fs in v['schema'].items():
                if 'data_relation' in fs and fs['data_relation']:
                    rel_name = fs['data_relation']['resource']
                    fld = peewee.ForeignKeyField(self.models[rel_name], **args)

                    # m:m
                    if fs['type'] == 'list':
                        self.link_tables[res_name +'_'+ rel_name] = (res_name, rel_name)
                    # 1:m
                    else:
                        fld.add_to_class(self.models[res_name], field_name)

        for tn,lt in self.link_tables.items():
            if not isinstance(lt, tuple): continue
            linkbase = {'Meta':Meta}
            # peewee adds _id suffix for fkeys
            linkbase[lt[0]] = peewee.ForeignKeyField(self.models[lt[1]])
            linkbase[lt[1]] = peewee.ForeignKeyField(self.models[lt[0]])
            mod = type(tn, (BaseModel,), linkbase)
            # TRIVIA: if unitialized Model is added to list with += it causes
            # Model.__iter__ to call select() on non-existing table
            self.link_tables[tn] = mod

            #if 'datasource' in v and 'source' in v['datasource']:

        #import pdb; pdb.set_trace()
        self.driver.create_tables(self.models.values() + self.link_tables.values(), safe=True)

    def _find(self, resource, req, **lookup):
        # TODO lookup?
        sort = []
        spec = {}

        if req.where:
            # could map mongo-style and_, or_ to peewee ops for eve/sqla compatibility
            try:
                spec = json.loads(req.where)
            except ValueError as exc:
                self.app.logger.exception(exc)
                abort(400, description='Unable to parse `where` clause')

        if config.VALIDATE_FILTERS:
            bad_filter = validate_filters(spec, resource)
            if bad_filter:
                abort(400, bad_filter)

        if config.DOMAIN[resource]['soft_delete'] and not req.show_deleted:
            # Soft delete filtering applied after validate_filters call as
            # querying against the DELETED field must always be allowed when
            # soft_delete is enabled
            spec[config.DELETED+'__ne'] = True;
            #if not self.query_contains_field(spec, config.DELETED):
            #    spec = self.combine_queries(
            #        spec, {config.DELETED: {"$ne": True}})

        model = self._get_model_cls(resource)

        if req.sort:
            for sort_arg in [s.strip() for s in req.sort.split(",")]:
                sn = sort_arg[1:] if sort_arg[0] == "-" else sort_arg
                try:
                    if sort_arg[0] == "-":
                        sort.append(getattr(model, sn).desc())
                    else:
                        sort.append(getattr(model, sn))
                except AttributeError:
                    abort(400, description='Unknown field name: %s' % sn)

        op = model.select()

        op = self._parse_where(op, spec)

        if len(sort):
            op = op.order_by(*sort)

        return op

    def find_one(self, resource, req, **lookup):
        rs = self._find(resource, req, lookup=lookup).limit(1).dicts()
        return rs[0] if rs.count() else None

    def find(self, resource, req, sub_resource_lookup):
        op = self._find(resource, req, lookup=sub_resource_lookup)

        if req.max_results:
            op = op.limit(req.max_results)
        if req.page > 1:
            op = op.offset((req.page - 1) * req.max_results)

        rs = op.execute()
        rs.__class__ = EvePeeweeResultWrapper
        rs._count = op.count(clear_limit=True)

        return rs


    def insert(self, resource, doc_or_docs):
        """Called when performing POST request"""
        if not isinstance(doc_or_docs, list):
            doc_or_docs = [doc_or_docs]
        ids = []

        try:
            for doc in doc_or_docs:
                model = self._doc_to_model(resource, doc)
                dt = datetime.now()
                model._created = dt
                model._updated = dt
                model.save()
                id = getattr(model, config.ID_FIELD)
                ids.append(id)
                # TODO: query the stored data in case triggers change it?
                doc[config.ID_FIELD] = id
            return ids

        except Exception as exc:
            self._handle_exception(exc)


    def update(self, resource, id_, updates, original):
        """Called when performing PATCH request."""
        cls = self._get_model_cls(resource)

        model = cls.get(getattr(cls, config.ID_FIELD) == id_)
        model._updated = datetime.now()

        for k,v in updates.items():
            setattr(model, k, v)

        try:
            model.save()
        except Exception as exc:
            self._handle_exception(exc)


    def replace(self, resource, id_, document, original):
        """Called when performing PUT request."""
        cls = self._get_model_cls(resource)
        model = self._doc_to_model(resource, document)
        setattr(model, config.ID_FIELD, id_)

        try:
            model.save()
        except Exception as exc:
            self._handle_exception(exc)


    def remove(self, resource, lookup):
        """Called when performing DELETE request."""
        cls = self._get_model_cls(resource)

        op = cls.delete()
        op = self._parse_where(op, lookup)

        try:
            op.execute()
        except Exception as exc:
            self._handle_exception(exc)


    def __getattr__(cls, attr):
        """placeholder for unimplemented methods"""
        default = classmethod(lambda cls: "Default class method for " + repr(cls))
        setattr(cls, attr, default)

        return getattr(cls, attr)


