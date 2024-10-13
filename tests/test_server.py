import os
import json
from time import sleep
from urllib import request
from urllib.error import URLError
from unittest import TestCase

from simple_http_server.daemon import HTTPd

import logging

# logging
_logger = logging.getLogger(__name__)


def set_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "{asctime} {name:25} ({process}) {levelname:>6} : {message}", style="{"
        )
    )
    _logger.addHandler(handler)

    if (level := os.environ.get("LOGLEVEL")) not in [
        "INFO",
        "ERROR",
        "DEBUG",
        "WARNING",
    ]:
        level = logging.DEBUG

    _logger.setLevel(level)
    logging.getLogger("simple_http_server").setLevel(level)


set_logging()


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
        timeout = 3
        attempt_nr = 0
        while True:
            attempt_nr += 1
            _logger.info("Probing connection (attempt #%d) ..." % attempt_nr)
            try:
                res = request.urlopen(req_head)
            except URLError as e:
                if attempt_nr < timeout:
                    _logger.info("... not ready yet")
                else:
                    _logger.error("timeout exceeded!")
                    raise e
            else:
                _logger.info("... ready!")
                break
            sleep(1)

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
