import json
from time import sleep
from urllib import request
from unittest import TestCase

from simple_http_server.httpd import HTTPd
from simple_http_server.log_handler import loghandler

import logging

# logging
_logger = logging.getLogger(__name__)
_logger.addHandler(loghandler)
_logger.setLevel(logging.DEBUG)
logging.getLogger("simple_http_server").setLevel(logging.DEBUG)


class HTTPdContextMgrTestCase(TestCase):
    def test_context_manager(self):
        address = "localhost"
        port = 8000
        base_url = f"http://{address}:{port}"
        req_head = request.Request(base_url, method="HEAD")

        # start server
        _logger.info("Starting HTTP server in context manager")
        with HTTPd(address=address, port=port) as httpd:
            self.assertTrue(httpd.is_alive())
            res = request.urlopen(req_head)

        self.assertEqual(res.code, 200)


class HTTPdTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        address = "localhost"
        port = 8000
        cls.base_url = f"http://{address}:{port}"

        # start server
        cls.httpd = HTTPd(address=address, port=port)
        _logger.debug("Starting HTTP server")
        cls.httpd.start()

    def test_httpd_is_alive(self):
        self.assertTrue(self.httpd.is_alive())

    def test_connection(self):
        req_head = request.Request(self.base_url, method="HEAD")
        res = request.urlopen(req_head)
        self.assertEqual(res.code, 200)

    def test_get_request(self):
        path = "/foo/bar"
        req = request.Request(f"{self.base_url}{path}")
        req.add_header("Content-Type", "application/json")
        with request.urlopen(req) as res:
            self.assertEqual(res.code, 200)
            res_bbody = res.read(res.length)
            _logger.info("response body: %s" % res_bbody.decode())
            res_obj = json.loads(res_bbody.decode())
            self.assertEqual(res_obj, {"foo": "bar"})

    @classmethod
    def tearDownClass(cls):
        _logger.debug("Stopping HTTP server")
        cls.httpd.stop()
