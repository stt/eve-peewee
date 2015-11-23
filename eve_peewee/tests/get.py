import pytest
import json

from datetime import datetime
from eve.tests.utils import DummyEvent
from eve.utils import date_to_str, str_to_date

from eve_peewee.tests import TestBaseSQL


class TestGetSQL(TestBaseSQL):

    def test_get_empty_resource(self):
        response, status = self.get(self.empty_resource)
        self.assert404(status)

    def test_get_page(self):
        response, status = self.get(self.known_resource)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 1, 101, 25)

        page = 1
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 2)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 1, 101, 25)

        page = 2
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertNextLink(links, 3)
        self.assertPrevLink(links, 1)
        self.assertLastLink(links, 5)
        self.assertPagination(response, 2, 101, 25)

        page = 5
        response, status = self.get(self.known_resource,
                                    '?page=%d' % page)
        self.assert200(status)

        links = response['_links']
        self.assertPrevLink(links, 4)
        self.assertLastLink(links, None)
        self.assertPagination(response, 5, 101, 25)

    def test_get_max_results(self):
        maxr = 10
        response, status = self.get(self.known_resource,
                                    '?max_results=%d' % maxr)
        self.assert200(status)

        resource = response['_items']
        self.assertEqual(len(resource), maxr)

        maxr = self.app.config['PAGINATION_LIMIT'] + 1
        response, status = self.get(self.known_resource,
                                    '?max_results=%d' % maxr)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_LIMIT'])

    def test_get_paging_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['pagination'] = False
        response, status = self.get(self.known_resource, '?page=2')
        self.assert200(status)
        resource = response['_items']
        self.assertFalse(len(resource) ==
                         self.app.config['PAGINATION_DEFAULT'])
        self.assertTrue(self.app.config['META'] not in response)
        links = response['_links']
        self.assertTrue('next' not in links)
        self.assertTrue('prev' not in links)

    def test_get_paging_disabled_no_args(self):
        self.app.config['DOMAIN'][self.known_resource]['pagination'] = False
        response, status = self.get(self.known_resource)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.known_resource_count)
        self.assertTrue(self.app.config['META'] not in response)
        links = response['_links']
        self.assertTrue('next' not in links)
        self.assertTrue('prev' not in links)

    """TODO
    def test_get_projection(self):
        projection = '{"firstname": 1}'
        response, status = self.get(self.known_resource, '?projection=%s' %
                                    projection)
        self.assert200(status)

        resource = response['_items']

        for r in resource:
            self.assertFalse('lastname' in r)
            self.assertFalse('fullname' in r)
            self.assertTrue('firstname' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['ETAG'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)
            self.assertTrue(r[self.app.config['LAST_UPDATED']] != self.epoch)
            self.assertTrue(r[self.app.config['DATE_CREATED']] != self.epoch)

        projection = '{"firstname": 0}'
        response, status = self.get(self.known_resource, '?projection=%s' %
                                    projection)
        self.assert200(status)

        resource = response['_items']

        for r in resource:
            self.assertFalse('firstname' in r)
            self.assertTrue('lastname' in r)
            self.assertTrue('fullname' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['ETAG'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)
            self.assertTrue(r[self.app.config['LAST_UPDATED']] != self.epoch)
            self.assertTrue(r[self.app.config['DATE_CREATED']] != self.epoch)
    """

    def test_get_projection_noschema(self):
        self.app.config['DOMAIN'][self.known_resource]['schema'] = {}
        response, status = self.get(self.known_resource)
        self.assert200(status)

        resource = response['_items']

        # fields are returned anyway since no schema = return all fields
        for r in resource:
            self.assertTrue('firstname' in r)
            self.assertTrue('lastname' in r)
            #self.assertTrue('fullname' in r)
            self.assertTrue(self.app.config['ID_FIELD'] in r)
            self.assertTrue(self.app.config['LAST_UPDATED'] in r)
            self.assertTrue(self.app.config['DATE_CREATED'] in r)

    def test_get_where_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = []
        where = 'firstname == %s' % self.item_firstname
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])

    def test_get_sort_disabled(self):
        self.app.config['DOMAIN'][self.known_resource]['sorting'] = False
        sort = '[("prog",-1)]'
        response, status = self.get(self.known_resource,
                                    '?sort=%s' % sort)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])
        for i in range(len(resource)):
            self.assertEqual(self.response_item(response, i)['prog'], i)

    def test_get_default_sort(self):
        s = self.app.config['DOMAIN'][self.known_resource]['datasource']

        # set default sort to 'prog', desc.
        s['default_sort'] = [('prog', -1)]
        self.app.set_defaults()
        response, _ = self.get(self.known_resource)
        # TODO: fix sort
        #self.assertEqual(self.response_item(response, 0)['prog'], 100)

        # set default sort to 'prog', asc.
        s['default_sort'] = [('prog', 1)]
        self.app.set_defaults()
        response, _ = self.get(self.known_resource)
        self.assertEqual(self.response_item(response, 0)['prog'], 0)

#    why it should be 304?
#    def test_get_if_modified_since(self):
#        self.assertIfModifiedSince(self.known_resource_url)

    def test_cache_control(self):
        self.assertCacheControl(self.known_resource_url)

    def test_expires(self):
        self.assertExpires(self.known_resource_url)

    def test_get(self):
        response, status = self.get(self.known_resource)
        self.assert_get(response, status)

    def assert_get(self, response, status, resource=None):
        self.assert200(status)

        links = response['_links']
        self.assertEqual(len(links), 4)
        self.assertHomeLink(links)
        if not resource:
            resource = self.known_resource
        self.assertResourceLink(links, resource)
        self.assertNextLink(links, 2)

        resource = response['_items']
        self.assertEqual(len(resource), self.app.config['PAGINATION_DEFAULT'])

        for i in range(len(resource)):
            item = self.response_item(response, i)
            self.assertItem(item, self.known_resource)
            etag = item.get(self.app.config['ETAG'])
            self.assertTrue(etag is not None)

    """TODO
    def test_get_where_allowed_filters(self):
        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = \
            ['notreally']
        where = '{"firstname": "%s"}' % self.item_firstname
        r = self.test_client.get('%s%s' % (self.known_resource_url,
                                           '?where=%s' % where))
        self.assert400(r.status_code)
        self.assertTrue(b"'firstname' not allowed" in r.get_data())

        self.app.config['DOMAIN'][self.known_resource]['allowed_filters'] = \
            ['*']
        r = self.test_client.get('%s%s' % (self.known_resource_url,
                                           '?where=%s' % where))
        self.assert200(r.status_code)
    """
    def test_get_where_like(self):
        r = self.test_client.get("{0}{1}".format(
            self.known_resource_url,
            '?where={0}'.format(json.dumps({
                'firstname': 'like("john%")'
            }))
        ))
        self.assert200(r.status_code)

    def test_get_where_ilike(self):
        r = self.test_client.get("{0}{1}".format(
            self.known_resource_url,
            '?where={0}'.format(json.dumps({
                'firstname': 'ilike("john%")'
            }))
        ))
        self.assert200(r.status_code)

    def test_get_where_startswith(self):
        r = self.test_client.get("{0}{1}".format(
            self.known_resource_url,
            '?where={0}'.format(json.dumps({
                'firstname': 'startswith("john")'
            }))
        ))
        self.assert200(r.status_code)

    def test_get_with_post_override(self):
        # POST request with GET override turns into a GET
        headers = [('X-HTTP-Method-Override', 'GET')]
        r = self.test_client.post(self.known_resource_url, headers=headers)
        response, status = self.parse_response(r)
        self.assert_get(response, status)

    def test_get_custom_items(self):
        self.app.config['ITEMS'] = '_documents'
        response, _ = self.get(self.known_resource)
        self.assertTrue('_documents' in response and '_items' not in response)

    def test_get_custom_links(self):
        self.app.config['LINKS'] = '_navigation'
        response, _ = self.get(self.known_resource)
        self.assertTrue('_navigation' in response and '_links' not in response)

    """
    @pytest.mark.xfail(EVE < 5, run=False, reason='features not released yet')
    def test_get_custom_auto_document_fields(self):
        self.app.config['LAST_UPDATED'] = '_updated_on'
        self.app.config['DATE_CREATED'] = '_created_on'
        self.app.config['ETAG'] = '_the_etag'
        response, _ = self.get(self.known_resource)
        for document in response['_items']:
            self.assertTrue('_updated_on' in document)
            self.assertTrue('_created_on' in document)
            self.assertTrue('_the_etag' in document)

    def test_get_nested_resource(self):
        response, status = self.get('users/overseas')
        import pdb; pdb.set_trace()
        self.assert_get(response, status, 'users_overseas')
    """

    def test_get_resource_title(self):
        # test that resource endpoints accepts custom titles.
        self.app.config['DOMAIN'][self.known_resource]['resource_title'] = \
            'new title'
        response, _ = self.get(self.known_resource)
        self.assertTrue('new title' in response['_links']['self']['title'])
        # test that the home page accepts custom titles.
        response, _ = self.get('/')
        found = False
        for link in response['_links']['child']:
            if link['title'] == 'new title':
                found = True
                break
        self.assertTrue(found)

    """
    @pytest.mark.xfail(EVE < 6, run=False, reason='features not released yet')
    def test_get_ifmatch_disabled(self):
        # when IF_MATCH is disabled no etag is present in payload
        self.app.config['IF_MATCH'] = False
        response, status = self.get(self.known_resource)
        resource = response['_items']

        for r in resource:
            self.assertTrue(self.app.config['ETAG'] not in r)

    def test_get_ims_empty_resource(self):
        # test that a GET with a If-Modified-Since on an empty resource does
        # not trigger a 304 and returns a empty resource instead (#243).

        # get the resource and retrieve its IMS.
        r = self.test_client.get(self.known_resource_url)
        last_modified = r.headers.get('Last-Modified')

        import pdb; pdb.set_trace()
        self.assertTrue(last_modified is not None)

        # delete the whole resource content.
        r = self.test_client.delete(self.known_resource_url)

        # send a get with a IMS header from previous GET.
        r = self.test_client.get(self.known_resource_url,
                                 headers=[('If-Modified-Since',
                                           last_modified)])
        self.assert200(r.status_code)
        self.assertEqual(json.loads(r.get_data())['_items'], [])
    """

    def test_get_idfield_doesnt_exist(self):
        # test that a non-existing ID_FIELD will be silently handled when
        # building HATEOAS document link (#351).
        self.app.config['ID_FIELD'] = 'id'
        response, status = self.get(self.known_resource)
        self.assert200(status)

    def test_get_invalid_idfield_cors(self):
        """ test that #381 is fixed. """
        request = '/%s/badid' % self.known_resource
        self.app.config['X_DOMAINS'] = '*'
        r = self.test_client.get(request, headers=[('Origin', 'test.com')])
        self.assert404(r.status_code)

    def test_get_same_collection_different_resource(self):
        """ the 'users' resource is actually using the same db collection as
        'contacts'. Let's verify that base filters are being applied, and
        the right amount of items/links and the correct titles etc. are being
        returned. Of course 'contacts' itself has its own base filter, which
        excludes the 'users' (those with a 'username' field).
        response, status = self.get(self.different_resource)
        self.assert200(status)

        links = response['_links']
        self.assertEqual(len(links), 2)
        self.assertHomeLink(links)
        self.assertResourceLink(links, self.different_resource)

        resource = response['_items']
        self.assertEqual(len(resource), 5)

        for item in resource:
            # 'user' title instead of original 'contact'
            self.assertItem(item, self.known_resource)

        etag = item.get(self.app.config['ETAG'])
        self.assertTrue(etag is not None)
        """

    def test_documents_missing_standard_date_fields(self):
        """Documents created outside the API context could be lacking the
        LAST_UPDATED and/or DATE_CREATED fields.
        """
        """
        _db = self.app.data.driver
        firstname = 'Douglas'
        person = self.test_sql_tables.People(firstname=firstname,
                                             lastname='Adams', prog=1)
        _db.session.add(person)
        _db.session.flush()
        where = '{"firstname": "%s"}' % firstname
        response, status = self.get(self.known_resource, '?where=%s' % where)
        self.assert200(status)
        resource = response['_items']
        self.assertEqual(len(resource), 1)
        self.assertItem(resource[0])

        _db.session.rollback()
        """

    """
    def test_get_embedded(self):
        _db = self.app.data.driver

        # create random person
        fake_person = self.test_sql_tables.People.\
            from_tuple(self.random_people(1)[0])
        fake_person._created = datetime.now()
        fake_person._updated = datetime.now()
        _db.session.add(fake_person)
        _db.session.flush()
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.people_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.flush()

        invoices = self.domain['invoices']
        people = self.domain['people']

        # Test that we get 400 if can't parse dict
        embedded = 'not-a-dict'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert400(r.status_code)

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is False by default)
        embedded = '{"people": 1}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['people_id'], self.item_id)

        # Set field to be embedded
        invoices['schema']['people']['data_relation']['embeddable'] = True

        # Test that it works
        invoices['embedding'] = True
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        # Test that it ignores a bogus field
        embedded = '{"people": 1, "not-a-real-field": 1}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        # Test that it ignores a real field with a bogus value
        embedded = '{"people": 1, "number": "not-a-real-value"}'
        r = self.test_client.get('%s/%s' % (invoices['url'],
                                            '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        # Test that it works with item endpoint too
        r = self.test_client.get('%s/%s/%s' % (invoices['url'],
                                               self.invoice_id,
                                               '?embedded=%s' % embedded))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people_id' in content)

        # Test that invoices_collection relationship are correctly embedded in
        # a list of resources. Even if invoices_collection is not a resource
        # name.
        r = self.test_client.get('%s%s' % (people['url'],
                                 '?embedded={"invoices_collection":1}'))
        content = json.loads(r.get_data())
        self.assertTrue('invoices_collection' in content['_items'][0])
        # Ensure only the fields with projection=1 are in the embedded
        # resource['_id']
        self.assertTrue('people_id' in
                        content['_items'][0]['invoices_collection'][0])
        self.assertTrue('people' not in
                        content['_items'][0]['invoices_collection'][0])

        # Test invoices_collection is embedded without the people relation
        # because projection is disabled for this field
        r = self.test_client.get('%s/1%s' % (
            people['url'], '?embedded={"invoices_collection":1}'))
        content = json.loads(r.get_data())
        self.assertTrue('number' in content['invoices_collection'][0])
        self.assertTrue('people' not in content['invoices_collection'][0])

        _db.session.rollback()

    def test_get_default_embedding(self):
        _db = self.app.data.driver

        # create random person
        #fake_person = self.test_sql_tables.People.\
        #    from_tuple(self.random_people(1)[0])
        sql_tables['people'].create(**self.random_people(1)[0])
        fake_person._created = datetime.now()
        fake_person._updated = datetime.now()
        _db.session.add(fake_person)
        _db.session.flush()
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.person_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.flush()

        invoices = self.domain['invoices']

        # Turn default field embedding on
        invoices['embedded_fields'] = ['people']

        # Test that doesn't come embedded if asking for a field that
        # isn't embedded (global setting is False by default)
        r = self.test_client.get(invoices['url'])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['people_id'], self.item_id)

        # Set field to be embedded
        invoices['schema']['people']['data_relation']['embeddable'] = True

        # Test that global setting applies even if field is set to embedded
        invoices['embedding'] = False
        r = self.test_client.get(invoices['url'])
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue(content['_items'][0]['people_id'], self.item_id)

        # Test that it works
        invoices['embedding'] = True
        r = self.test_client.get('{0}?embedded={{"people": 1}}'.
                                 format(invoices['url']))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        # Test that it ignores a bogus field
        invoices['embedded_fields'] = ['people', 'not-really']
        r = self.test_client.get('{0}?embedded={{"people": 1}}'.
                                 format(invoices['url']))
        self.assert200(r.status_code)
        content = json.loads(r.get_data())
        self.assertTrue('people' in content['_items'][0].keys())

        _db.session.rollback()

    def test_cursor_extra_find(self):
        _find = self.app.data.find
        hits = {'total_hits': 0}

        def find(resource, req, sub_resource_lookup):
            def extra(response):
                response['_hits'] = hits
            cursor = _find(resource, req, sub_resource_lookup)
            cursor.extra = extra
            return cursor

        self.app.data.find = find
        r, status = self.get(self.known_resource)
        self.assert200(status)
        self.assertTrue('_hits' in r)
        self.assertEqual(r['_hits'], hits)

    def test_get_subresource(self):
        _db = self.app.data.driver

        # create random person
        fake_person = self.test_sql_tables.People.\
            from_tuple(self.random_people(1)[0])
        fake_person._created = datetime.now()
        fake_person._updated = datetime.now()
        _db.session.add(fake_person)
        _db.session.flush()
        fake_invoice = self.test_sql_tables.Invoices(number=4)
        fake_invoice.people_id = fake_person._id
        fake_invoice._created = datetime.now()
        fake_invoice._updated = datetime.now()
        _db.session.add(fake_invoice)
        _db.session.flush()

        # GET all invoices by new contact
        response, status = self.get('users/%s/invoices' % fake_person._id)
        self.assert200(status)
        # only 2 invoices
        self.assertEqual(len(response['_items']), 2)
        self.assertEqual(len(response['_links']), 2)
        # which links to the right contact
        self.assertEqual(response['_items'][1]['people'],
                         fake_person._id)

        _db.session.rollback()
    """
