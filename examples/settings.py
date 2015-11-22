DEBUG = True
URL_PREFIX = 'api'
ID_FIELD = 'id'
RESOURCE_METHODS = ['GET', 'POST', 'DELETE']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE', 'PUT']
ITEM_URL = 'regex("[a-f0-9]+")'

DATABASE_URI='postgres://stt:@psql1.n.kapsi.fi/stt'

DOMAIN={
  'house': {
    'item_lookup_field': 'id',
    'transparent_schema_rules': True,
    'schema': {
      'id': {
        'type': 'integer',
        'unique': True,
        '_peewee': { 'primary_key': True }
      },
      'address': {
        'type': 'string'
      },
      'features': {
        'type': 'dict'
      },
      'asd': {
        'type': 'float',
        'nullable': True
      }
    }
  }
}
