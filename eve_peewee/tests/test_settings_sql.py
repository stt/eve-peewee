# -*- coding: utf-8 -*-
import os

db_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'test.db')
DATABASE_URI = 'sqlite:///%s' % db_filename
DEBUG = True

RESOURCE_METHODS = ['GET', 'POST', 'DELETE']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE', 'PUT']

ID_FIELD = 'id'

VALIDATE_FILTERS = True

people = {'item_title': 'person',
#          'additional_lookup': {
#              'url': 'regex("[\w]+")',
#              'field': 'firstname'
#          },
          'cache_control': 'max-age=10,must-revalidate',
          'cache_expires': 10,
          'resource_methods': ['GET', 'POST', 'DELETE'],
          'schema': {
              #'invoices_collection': {
              #    'type': 'integer',
              #    'data_relation': {
              #        'embeddable': True,
              #        'resource': 'invoices'}}
            'firstname': {'type':'string', 'unique': True},
            'lastname': {'type':'string'},
            #'fullname': column_property(firstname + " " + lastname)
            'prog': {'type':'integer'},
#            'born': {'type':'datetime'},
#            'title': {'type':'string'}
  }
}


import copy
users = copy.deepcopy(people)
users['url'] = 'users'
users['datasource'] = {'source': 'People',
                       'filter': 'prog < 5'}
users['resource_methods'] = ['DELETE', 'POST', 'GET']
users['item_title'] = 'user'

users_overseas = copy.deepcopy(users)
users_overseas['url'] = 'users/overseas'
users_overseas['datasource'] = {'source': 'People'}

invoices = {
    'schema': {}
}

user_invoices = copy.deepcopy(invoices)
user_invoices['url'] = 'users/<regex("[0-9]+"):people>/invoices'
user_invoices['datasource'] = {'source': 'Invoices'}

payments = {
    'resource_methods': ['GET'],
    'item_methods': ['GET'],
    'schema': {}
}

DOMAIN = {
    'people': people,
    'users': users,
    'users_overseas': users_overseas,
#    'invoices': invoices,
    'userinvoices': user_invoices,
    'payments': payments
}
