import peewee
from playhouse.postgres_ext import Model, DateTimeField, PostgresqlExtDatabase, BinaryJSONField
from playhouse.db_url import parse
from eve.io.base import DataLayer, BaseJSONEncoder
from werkzeug.exceptions import HTTPException
import json, ast, operator
import traceback, sys

__version__ = '0.0.1'

import logging
logger = logging.getLogger(__name__)

"""
def find_subclasses(sub, mod=None):
    # same as vars() except with globals
    children = mod.__dict__ if mod else globals()
    classes = filter(
        lambda c: isinstance(c, type) and hasattr(c, '__bases__'),
        children.values())
    return [cls for cls in classes if cls != sub and issubclass(cls, sub)]

#db.create_tables(find_subclasses(project.models, BaseModel)
"""

class BaseModel(Model):
    _created = DateTimeField()
    _updated = DateTimeField()

    def __str__(self):
        r = {}
        for k in self._data.keys():
            try:
                r[k] = str(getattr(self, k))
            except:
                r[k] = json.dumps(getattr(self, k))
        return json.dumps(r)

    def __getitem__(self, key):
        if isinstance(key, int): raise StopIteration
        return getattr(self, key)

    __setitem__ = Model.__setattr__


class PeeweeJSONEncoder(BaseJSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return str(obj)
        else:
            return super(PeeweeJSONEncoder, self).default(obj)


class EvePeeweeResultWrapper(peewee.NaiveQueryResultWrapper):
    def __init__(self, wrapped_class):
        self.wrapped_class = wrapped_class

    def __getattr__(self, attr):
        return self.wrapped_class.__getattribute__(attr)

    def count(self, **kwargs):
        return super(EvePeeweeResultWrapper, self).count


class EvePeewee(DataLayer):
    json_encoder_class = PeeweeJSONEncoder

    def _get_model_cls(self, resource):
        try:
            return self.models[resource]
        except KeyError:
            abort(404)

    """
    def _update_etag(self, model):
        import hashlib
        h = hashlib.sha1()
        model._etag = h.hexdigest()
    """

    def _doc_to_model(self, resource, doc):
        if '_id' in doc:
            doc['id'] = doc.pop('_id')
        cls = self._get_model_cls(resource)
        instance = cls(**doc)
        """
        for attr, field in iteritems(cls._fields):
            if isinstance(field, FileField):
                if attr in doc:
                    proxy = field.get_proxy_obj(key=field.name,
                                                instance=instance)
                    proxy.grid_id = doc[attr]
                    instance._data[attr] = proxy
        """
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

    def init_app(self, app):
        url = parse(app.config['DATABASE_URI'])
        self.driver = PostgresqlExtDatabase(register_hstore=False, **url)
        self.config = app.config

        self.models = {}
        class Meta:
            database = self.driver
        for k, v in app.config['DOMAIN'].items():
            mod = type(k, (BaseModel,), {'Meta':Meta})
            for fn,fs in v['schema'].iteritems():
                # http://python-eve.org/config.html#schema
                # http://docs.peewee-orm.com/en/latest/peewee/models.html#fields
                pw_eve_fld_prop_map = {
                    'nullable': 'null', 'minlength': 'min_length', 'maxlength': 'max_length',
                    'default': 'default', 'unique': 'unique', 
                }
                pw_fld_props = ['primary_key','index']
                args = {pw_eve_fld_prop_map[k]: fs[k] for k in fs.keys() if k in pw_eve_fld_prop_map}
                #args.update({k:fs[k] for k in fs.keys() if k in pw_fld_props})
                if '_peewee' in fs:
                    args.update(fs['_peewee'])

                if 'primary_key' in args and args['primary_key']:
                    fld = peewee.PrimaryKeyField(**args)
                elif fs['type'] == 'string':
                    fld = peewee.TextField(**args)
                elif fs['type'] == 'boolean':
                    fld = peewee.BooleanField(**args)
                elif fs['type'] == 'integer':
                    fld = peewee.IntegerField(**args)
                elif fs['type'] == 'float' or fs['type'] == 'number':
                    fld = peewee.FloatField(**args)
                elif fs['type'] == 'datetime':
                    fld = peewee.DatetimeField(**args)
                elif fs['type'] == 'dict' or fs['type'] == 'list':
                    fld = BinaryJSONField(**args)
                # unsupported: objectid, media, geojson
                else:
                    raise TypeError("unknown: " + fs['type'])

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

        model = self._get_model_cls(resource)

        #clauses += [(User.f == 'v')]

        op = model.select()
        clauses = self._dict_to_clauses(model, spec)
        if len(clauses):
            op = op.where(reduce(operator.or_, clauses))

        return op

    def find_one(self, resource, req, **lookup):
        rs = self._find(resource, req, lookup=lookup).limit(1).dicts()
        logger.debug("%s", type(rs))

        return rs[0] if rs.count() else None

    def find(self, resource, req, sub_resource_lookup):
        """mongo ?where={"name": "john doe} or py ?where=name=="john doe"
        :param resource: resource name.
        :param req: a :class:`ParsedRequest`instance.
        :param sub_resource_lookup: sub-resource lookup from the endpoint url.
        """
        #args = {'sort': extract_sort_arg(req),  'resource': resource}
        op = self._find(resource, req, lookup=sub_resource_lookup)
        rs = EvePeeweeResultWrapper(op.execute())

        return rs


    def insert(self, resource, doc_or_docs):
        """Called when performing POST request"""
        if not isinstance(doc_or_docs, list):
            doc_or_docs = [doc_or_docs]
        ids = []

        try:
            for doc in doc_or_docs:
                model = self._doc_to_model(resource, doc)
                model.save()
                ids.append(model.id)
                # TODO: return data from db, in case triggers change it?
                doc[self.config['ID_FIELD']] = model.id
            return ids

        except Exception as exc:
            self._handle_exception(exc)


    def update(self, resource, id_, updates, original):
        """Called when performing PATCH request."""
        logger.debug("%s", updates)
        cls = self._get_model_cls(resource)

        model = cls.get(cls.id == id_)
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
        logger.error("DEFAULT "+repr(cls))
        default = classmethod(lambda cls: "Default class method for " + repr(cls))
        setattr(cls, attr, default)

        return getattr(cls, attr)


