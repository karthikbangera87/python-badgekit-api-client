import httpretty
import hashlib
import requests
from badgekit import jwt_auth
import jws
import unittest

def from_jwt(jwt, key):
    (b64_header, b64_claim, b64_sig) = jwt.split('.')
    (header, claim) = map(jws.utils.from_base64,
            (b64_header, b64_claim))
    jws.verify(header, claim, b64_sig, key, is_json=True)
    return jws.utils.decode(b64_claim)

class BKAPITest(unittest.TestCase):
    @httpretty.activate
    def test_auth(self):
        httpretty.register_uri(httpretty.GET, 'http://example.com/',
                body='{"app": "BadgeKit API"}')

        secret = 's3cr3tz'

        auth = jwt_auth.JWTAuth(secret)
        auth.add_field('path', jwt_auth.payload_path)
        auth.add_field('method', jwt_auth.payload_method)
        resp = requests.get('http://example.com/', auth=auth)
        self.assert_(resp)

        req = httpretty.last_request()
        self.assert_('Authorization' in req.headers, 'JWT Authorization present')

        auth_hdr = req.headers['Authorization']
        self.assert_('JWT token=' in auth_hdr)
        token = auth_hdr[auth_hdr.find('"'):].strip('"')
        # Throws an exception on failure to verify
        claim = from_jwt(token, secret)

    @httpretty.activate
    def test_body(self):
        httpretty.register_uri(httpretty.POST, 'http://example.com/',
                body='[]')
        secret = 's33333krit'

        auth = jwt_auth.JWTAuth(secret)
        auth.add_field('body', jwt_auth.payload_body)
        resp = requests.post('http://example.com/',
                data={'Hope this': 'Is encoded'},
                auth=auth)

        req = httpretty.last_request()
        auth_hdr = req.headers['Authorization']
        token = auth_hdr[auth_hdr.find('"'):].strip('"')
        claim = from_jwt(token, secret)

        self.assertEqual(claim['body']['hash'],
                hashlib.sha256(req.body).hexdigest())

    @httpretty.activate
    def test_query(self):
        "Make sure query strings are included in the 'path' claim"
        httpretty.register_uri(httpretty.GET, 'http://example.com/',
                body='[]')
        secret = 's33333krit'

        auth = jwt_auth.JWTAuth(secret)
        auth.add_field('path', jwt_auth.payload_path)
        resp = requests.get('http://example.com/',
                params={'Hope this': 'Is signed'},
                auth=auth)

        req = httpretty.last_request()
        auth_hdr = req.headers['Authorization']
        token = auth_hdr[auth_hdr.find('"'):].strip('"')
        claim = from_jwt(token, secret)

        self.assertEqual(claim['path'], '/?Hope+this=Is+signed')