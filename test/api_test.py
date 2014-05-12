import httpretty
import requests
import re
import unittest
from badgekit import api
import jwt
import json


class BKAPITest(unittest.TestCase):
    @httpretty.activate
    def test_auth_params(self):
        httpretty.register_uri(httpretty.GET, 'http://example.com/',
                body='{"app": "BadgeKit API"}')

        a = api.BadgeKitAPI('http://example.com', 's3cr3t')
        self.assert_(a.ping())

        req = httpretty.last_request()
        self.assert_('Authorization' in req.headers, 'JWT Authorization present')

        auth_hdr = req.headers['Authorization']
        self.assert_('JWT token=' in auth_hdr)
        token = auth_hdr[auth_hdr.find('"'):].strip('"')
        # Throws an exception on failure to verify
        claim = jwt.decode(token, 's3cr3t')

        self.assert_('key' in claim)
        self.assert_('exp' in claim)
        self.assertEqual(claim['path'], '/')
        self.assertEqual(claim['method'], 'GET')

    @httpretty.activate
    def test_list(self):
        a = api.BadgeKitAPI('http://example.com', 'asdf')

        ret_structure = {
                u'badges': [u'real data goes here'],
                }
        httpretty.register_uri(httpretty.GET,
                re.compile('example.com/.*'),
                body=json.dumps(ret_structure))

        badges = a.list('badge', system='badgekit')
        self.assertEqual(badges, ret_structure)

        req = httpretty.last_request()
        self.assertEqual(req.path, '/systems/badgekit/badges')

    @httpretty.activate
    def test_get(self):
        a = api.BadgeKitAPI('http://example.com/', 'asdf')

        slug = u'the-machine'
        ret_structure = { u'system':
                { u'email': None, u'id': 1, u'imageUrl': None, u'slug': slug },
                }
        httpretty.register_uri(httpretty.GET,
                re.compile('example.com/.*'),
                body=json.dumps(ret_structure))

        resp = a.get(system=slug)
        self.assertEqual(resp['system'], ret_structure[u'system'])

        req = httpretty.last_request()
        self.assertEqual(req.path, '/systems/the-machine')

    @httpretty.activate
    def test_create(self):
        a = api.BadgeKitAPI('http://example.com/', 'asdf')

        slug = u'test-sys'
        httpretty.register_uri(httpretty.POST,
                re.compile('example.com/.*'),
                body='{}', status=201)

        result = a.create(
                'system',
                dict(slug=slug, name='Test System FTW',
                    url='http://example.com/testz'))

        req = httpretty.last_request()
        self.assertEqual(req.path, '/systems')


class PathTest(unittest.TestCase):
    def test_system_path(self):
        c = dict(system='mysystem')
        self.assertEqual(api._make_path(**c), 'systems/mysystem')

    def test_issuer_path(self):
        c = dict(system='sys', issuer='iss')
        self.assertEqual(api._make_path(**c), 'systems/sys/issuers/iss')

    def test_extra_bits(self):
        c = dict(system='sass')
        self.assertEqual(
                api._make_path('badges', **c),
                'systems/sass/badges')

    def test_query(self):
        self.assertEqual(
                api._make_path('badges', system='jkl', archived=True),
                'systems/jkl/badges?archived=true')


class ExceptionTest(unittest.TestCase):
    def test_known_str(self):
        req = requests.Request("POST", "http://example.org/system/")
        response = {
                "code": "ResourceConflict",
                "message": "system with that `slug` already exists",
                "details": {
                    "slug": "system-slug",
                    "name": "System Name",
                    "url": "https://example.org/system/",
                    "email": "system-badges@example.org",
                    "description": "System Description"
                    }
                }
        e = api.ResourceConflict(response, req)
        self.assert_('ResourceConflict' in str(e))
        self.assert_('already exists' in str(e))
