import peewee
from playhouse import db_url

from eve.io.base import DataLayer, BaseJSONEncoder
from werkzeug.exceptions import HTTPException

from datetime import datetime
import time, json, ast, operator
import traceback, sys

__version__ = '0.0.2'

import logging
logger = logging.getLogger(__name__)


class BaseModel(peewee.Model):
    _created = peewee.DateTimeField()
    _updated = peewee.DateTimeField()
    _config = {}

    def __repr__(self):
        r = {}
        for k,v in self._data.iteritems():
            try:
                is_dt = isinstance(v, datetime)
                if is_dt and 'DATE_FORMAT' in self._config:
                    r[k] = v.strftime(self._config['DATE_FORMAT'])
                elif isinstance(v, int) or isinstance(v, dict):
                    r[k] = v
                else:
                    r[k] = str(v)
            except:
                r[k] = json.dumps(v)
        return json.dumps(r)

    def __contains__(self, key):
        """
        eve.methods.common.build_response_document checks if
        `resource_def['id_field'] in document` before adding _links
        """
        return key in self._data

    def __getitem__(self, key):
        if isinstance(key, int): raise StopIteration
        return self._data[key]

    def __setitem__(self, key, val):
        self._data[key] = val


class PeeweeJSONEncoder(BaseJSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return str(obj)
        else:
            return super(PeeweeJSONEncoder, self).default(obj)


class EvePeeweeResultWrapper(peewee.NaiveQueryResultWrapper):
    def count(self, **kwargs):
        if hasattr(self, '_count'):
            return self._count
        else:
            return super(EvePeeweeResultWrapper, self).count


def validate_filters(where, resource):
    allowed = config.DOMAIN[resource]['allowed_filters']
    if '*' not in allowed:
        for filt in where:
            key = filt.left.key
            if key not in allowed:
                return "filter on '%s' not allowed" % key
    return None


class EvePeewee(DataLayer):
    json_encoder_class = PeeweeJSONEncoder

    def _get_model_cls(self, resource):
        try:
            return self.models[resource]
        except KeyError:
            abort(404)

    def _doc_to_model(self, resource, doc):
        if '_id' in doc:
            doc['id'] = doc.pop('_id')
        cls = self._get_model_cls(resource)
        instance = cls(**doc)
        return instance

    def _handle_exception(self, exc):
        if self.app.debug:
            traceback.print_exc(file=sys.stderr)
        raise exc

    def _parse_where(self, where):
        try:
            return json.loads(where)
        except HTTPException as e:
            # _sanitize() is raising an HTTP exception; let it fire.
            raise
        except:
            #logger.exception("failed to parse where: %s", req.where)
            #ast.literal_eval?
            abort(400, description=debug_error_message(
                'Unable to parse `where` clause'
            ))

    def _dict_to_clauses(self, model, spec):
        return [(getattr(model, f) == spec[f]) for f in spec.keys()]

    def _get_fieldtype(self, name):
        fld = None
        if name == 'string':
            fld = peewee.TextField
        elif name == 'boolean':
            fld = peewee.BooleanField
        elif name == 'integer':
            fld = peewee.IntegerField
        elif name == 'float' or name == 'number':
            fld = peewee.FloatField
        elif name == 'datetime':
            fld = peewee.DateTimeField
        elif name == 'dict' or name == 'list':
            from playhouse.postgres_ext import BinaryJSONField
            fld = BinaryJSONField
        return fld
 
    def init_app(self, app):
        if 'DATABASE_URI' in app.config:
            if app.config['DATABASE_URI'].startswith('postgres'):
                url = db_url.parse(app.config['DATABASE_URI'])
                from playhouse.postgres_ext import PostgresqlExtDatabase
                self.driver = PostgresqlExtDatabase(register_hstore=False, **url)
            else:
                self.driver = db_url.connect(app.config['DATABASE_URI'])
        self.config = app.config

        # http://python-eve.org/config.html#schema
        # http://docs.peewee-orm.com/en/latest/peewee/models.html#fields
        pw_eve_fld_prop_map = {
            'nullable': 'null', 'minlength': 'min_length', 'maxlength': 'max_length',
            'default': 'default', 'unique': 'unique', 
        }
        pw_fld_props = ['primary_key','index']

        self.models = {}
        class Meta:
            database = self.driver

        for k, v in app.config['DOMAIN'].items():
            mod = type(k, (BaseModel,), {'Meta':Meta})
            mod._config = app.config
            if 'schema' not in v: continue

            for fn,fs in v['schema'].iteritems():
                args = {pw_eve_fld_prop_map[k]: fs[k] for k in fs.keys() if k in pw_eve_fld_prop_map}
                #args.update({k:fs[k] for k in fs.keys() if k in pw_fld_props})
                if '_peewee' in fs:
                    args.update(fs['_peewee'])

                if 'primary_key' in args and args['primary_key']:
                    fld = peewee.PrimaryKeyField(**args)
                # unsupported: objectid, media, geojson
                else:
                    fld = self._get_fieldtype(fs['type'])
                    if not fld:
                        raise TypeError("unknown: " + fs['type'])
                    fld = fld(**args)

                fld.add_to_class(mod, fn)

            self.models[k] = mod
            """
            # If a resource has a relation, copy the properties of the relation
            if 'datasource' in v and 'source' in v['datasource']:
                source = v['datasource']['source']
                source = app.config['DOMAIN'].get(source.lower())
                print source
                if source:
                    v['schema'] = source['schema']
                    v['item_lookup_field'] = source['item_lookup_field']
                    v['item_url'] = source['item_url']
            """

        #import pdb; pdb.set_trace()
        self.driver.create_tables(self.models.values(), safe=True)

    def _find(self, resource, req, **lookup):
        spec = {}
        if req.sort:
            try:
                client_sort = ast.literal_eval(req.sort)
            except Exception as e:
                abort(400, description=debug_error_message(str(e)))

        if req.where:
            spec = self._parse_where(req.where)

        #bad_filter = validate_filters(spec, resource)
        #if bad_filter:
        #    abort(400, bad_filter)

        model = self._get_model_cls(resource)

        #clauses += [(User.f == 'v')]

        op = model.select()
        clauses = self._dict_to_clauses(model, spec)
        if len(clauses):
            op = op.where(reduce(operator.or_, clauses))

        return op

    def find_one(self, resource, req, **lookup):
        rs = self._find(resource, req, lookup=lookup).limit(1).dicts()
        return rs[0] if rs.count() else None

    def find(self, resource, req, sub_resource_lookup):
        """mongo ?where={"name": "john doe} or py ?where=name=="john doe"
        :param resource: resource name.
        :param req: a :class:`ParsedRequest`instance.
        :param sub_resource_lookup: sub-resource lookup from the endpoint url.
        """
        #args = {'sort': extract_sort_arg(req),  'resource': resource}
        op = self._find(resource, req, lookup=sub_resource_lookup)
        if req.max_results:
            op = op.limit(req.max_results)
        if req.sort:
            print req.sort
            op = op.order_by(req.sort)
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
                ids.append(model.id)
                # TODO: return data from db, in case triggers change it?
                doc[self.config['ID_FIELD']] = model.id
            return ids

        except Exception as exc:
            self._handle_exception(exc)


    def update(self, resource, id_, updates, original):
        """Called when performing PATCH request."""
        cls = self._get_model_cls(resource)

        model = cls.get(cls.id == id_)
        dt = datetime.now()
        model._updated = dt
        for k,v in updates.iteritems():
            setattr(model, k, v)

        try:
            model.save()
        except Exception as exc:
            self._handle_exception(exc)


    def replace(self, resource, id_, document, original):
        """Called when performing PUT request."""
        cls = self._get_model_cls(resource)
        model = self._doc_to_model(resource, document)
        model.id = id_

        try:
            model.save()
        except Exception as exc:
            self._handle_exception(exc)


    def remove(self, resource, lookup):
        """Called when performing DELETE request."""
        cls = self._get_model_cls(resource)

        op = cls.delete()
        clauses =  self._dict_to_clauses(cls, lookup)
        if len(clauses):
            op = op.where(reduce(operator.or_, clauses))
        #else: DANGER

        try:
            op.execute()
        except Exception as exc:
            self._handle_exception(exc)


    def __getattr__(cls, attr):
        default = classmethod(lambda cls: "Default class method for " + repr(cls))
        setattr(cls, attr, default)

        return getattr(cls, attr)


