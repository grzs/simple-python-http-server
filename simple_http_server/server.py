#!/usr/bin/env python3

import signal
import socket
from selectors import DefaultSelector, EVENT_READ

from io import BytesIO, TextIOWrapper
import json
from http.server import (
    HTTPStatus,
    HTTPServer,
    ThreadingHTTPServer,
    BaseHTTPRequestHandler,
    SimpleHTTPRequestHandler,
)
from http.client import HTTPMessage
from urllib import parse
import re
import os

import logging

_loghandler = logging.StreamHandler()
_loghandler.setFormatter(
    logging.Formatter(
        "{asctime} {name} ({process}) {levelname:6} : {message}", style="{"
    )
)
_logger = logging.getLogger(__name__)
_logger.addHandler(_loghandler)

INTERRUPT_READ, INTERRUPT_WRITE = socket.socketpair()
SERVER_CLASS = HTTPServer if os.environ.get("DEBUG") else ThreadingHTTPServer


# degine and register signal handler
def signal_handler(signum, frame):
    _logger.debug("HTTPd signal handler called with signal %d" % signum)
    INTERRUPT_WRITE.send(b"\0")


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class RequestHandler(BaseHTTPRequestHandler):
    def _headers_iget(self, key, default=None):
        """insensitive search in headers by key"""
        for h_key in self.headers.keys():
            if h_key.lower() == key.lower():
                return self.headers.get(h_key)
        return default

    def _preprocess(self):
        self.response_body = TextIOWrapper(BytesIO(), newline="\n")
        self.response_headers = HTTPMessage()

        # content type
        self.content_type = self._headers_iget("content-type", "text/plain").lower()

        # parse header
        path_parts = parse.urlsplit(self.path)
        self.path_path = path_parts.path
        self.query_params = parse.parse_qs(path_parts.query)
        self.fragment = path_parts.fragment

    def _preprocess_body(self):
        self.body_size = int(self._headers_iget("content-length", 0))
        self.bbody = self.rfile.read(self.body_size)

    def _flush_response_body(self):
        """write response_body buffer to output output stream"""

        self.response_body.seek(0)
        self.wfile.write(self.response_body.buffer.read())

    def log_message(self, format, *args):
        """Log an arbitrary message.

        This is used by all other logging functions.  Override
        it if you have specific logging wishes.

        The first argument, FORMAT, is a format string for the
        message to be logged.  If the format string contains
        any % escapes requiring parameters, they should be
        specified as subsequent arguments (it's just like
        printf!).

        The client ip and current date/time are prefixed to
        every message.

        Unicode control characters are replaced with escaped hex
        before writing the output to stderr.

        """

        message = format % args
        _logger.info(
            "%s - - %s"
            % (
                self.address_string(),
                # self.log_date_time_string(),
                message.translate(self._control_char_table),
            )
        )

    def send_response_headers_body(self):
        status_code = self.dispatch()
        self.response_headers.add_header("Content-type", self.content_type)

        if status_code >= 400:
            self.send_error(HTTPStatus(status_code))
        self.send_response(HTTPStatus(status_code))

        # send headers
        for key, value in self.response_headers.items():
            self.send_header(key, value)
        self.end_headers()

        self._flush_response_body()

    def do_HEAD(self):
        """Serve a HEAD request."""

        self.send_response(HTTPStatus.OK)
        self.end_headers()

    def do_GET(self):
        """Serve a GET request."""

        self._preprocess()
        self.send_response_headers_body()

    def do_POST(self):
        """Serve a POST request."""

        self._preprocess()
        self.process_body()

        # send response
        self.send_response_headers_body()

    # methods to override
    def process_body(self):
        if self.content_type == "application/json":
            _logger.debug("body", json.loads(self.bbody.decode()))
        else:
            _logger.debug("body:", self.bbody.decode())

    def dispatch(self):
        _logger.debug("Content-Type: %s" % self.content_type)
        if re.search(r"\.[a-z0-9]+$", self.path_path):
            return self.serve_file()
        elif self.content_type == "application/x-www-form-urlencoded":
            return self.serve_form()
        elif self.content_type == "application/json":
            return self.serve_json()
        else:
            return 404

    def serve_form(self):
        _logger.debug(self.query_params)
        return 200

    def serve_file(self):
        file_path = self.path_path[1:]
        if os.path.isfile(file_path):
            with open(file_path) as f:
                self.response_body.seek(0)
                self.response_body.write(f.read())
                self.response_headers.add_header(
                    "Content-Length", str(self.response_body.tell())
                )
                return 200
        else:
            return 404

    def serve_json(self):
        if self.path_path == "/":
            data = {}
            return 200

        path = self.path_path.split("/")
        if len(path) == 2:
            data = path[1]
        elif len(path) == 3:
            data = {path[1]: path[2]}
        else:
            data = path[1:]

        # dump json to response_body buffer
        self.response_body.seek(0)
        json.dump(data, self.response_body)
        self.response_headers.add_header(
            "Content-Length", str(self.response_body.tell())
        )
        return 200


def run_simple(address="", port=8000):
    httpd = SERVER_CLASS((address, port), SimpleHTTPRequestHandler)
    httpd.serve_forever()


def run(address="", port=8000):
    httpd = SERVER_CLASS((address, port), RequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _logger.info("\nGood bye!")


def run_listener(address="", port=8000, request_handler=RequestHandler):
    httpd = SERVER_CLASS((address, port), request_handler)

    sel = DefaultSelector()
    sel.register(INTERRUPT_READ, EVENT_READ)
    sel.register(httpd, EVENT_READ)

    while True:
        for key, _ in sel.select():
            if key.fileobj == INTERRUPT_READ:
                INTERRUPT_READ.recv(1)
                return
            if key.fileobj == httpd:
                httpd.handle_request()


if __name__ == "__main__":
    run()
