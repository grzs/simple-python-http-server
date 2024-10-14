import os
import json
from urllib import request
from unittest import TestCase

from simple_http_server.request_handler import RequestHandler
from simple_http_server.httpd import HTTPd
from simple_http_server.log_handler import loghandler

import logging

# logging
_logger = logging.getLogger(__name__)
_logger.addHandler(loghandler)
_logger.setLevel(logging.DEBUG)
logging.getLogger("simple_http_server").setLevel(logging.DEBUG)

DUMP_REQUEST_DIR = "/tmp/test_requests/"


class RequestHandlerTest(RequestHandler):
    dump_request_dir = DUMP_REQUEST_DIR


class HTTPdContextMgrTestCase(TestCase):
    def test_context_manager(self):
        address = "localhost"
        port = 8000
        base_url = f"http://{address}:{port}"
        req_head = request.Request(base_url, method="HEAD")

        # start server
        _logger.info("Starting HTTP server in context manager")
        with HTTPd(
            address=address, port=port, request_handler=RequestHandlerTest
        ) as httpd:
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
        cls.httpd = HTTPd(
            address=address, port=port, request_handler=RequestHandlerTest
        )
        _logger.debug("Starting HTTP server")
        cls.httpd.start()

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

        self.assertTrue(os.path.isdir(DUMP_REQUEST_DIR))
        dump_files = os.listdir(DUMP_REQUEST_DIR)
        self.assertGreater(len(dump_files), 0)

        dump_files.sort()
        file_name = dump_files[-1]
        self.assertTrue(file_name.endswith(".json"))

        file_path = os.path.join(DUMP_REQUEST_DIR, file_name)
        self.assertTrue(os.path.isfile(file_path))

        _logger.info("parsing file %s" % file_path)

        with open(file_path) as f:
            data = json.load(f)

        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("method"), "GET")
        self.assertEqual(data.get("url").get("path"), "/foo/bar")
        self.assertEqual(data.get("headers").get("Content-Type"), "application/json")

    @classmethod
    def tearDownClass(cls):
        _logger.debug("Stopping HTTP server")
        cls.httpd.stop()

        if os.environ.get("HTTPD_TEST_KEEP_DUMP_FILES"):
            return

        _logger.debug("Cleaning up files")
        try:
            for dmp_file in os.listdir(DUMP_REQUEST_DIR):
                os.unlink(os.path.join(DUMP_REQUEST_DIR, dmp_file))
            os.rmdir(DUMP_REQUEST_DIR)
        except FileNotFoundError as e:
            _logger.error(e)
