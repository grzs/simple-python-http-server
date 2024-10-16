from io import BytesIO, TextIOWrapper
from http.server import BaseHTTPRequestHandler, HTTPStatus
from http.client import HTTPMessage
from urllib import parse
import re
import os
import json
import datetime
from base64 import b64encode
import logging

from .log_handler import loghandler, loglevel

_logger = logging.getLogger(__name__)
_logger.addHandler(loghandler)
_logger.setLevel(loglevel)


class RequestHandler(BaseHTTPRequestHandler):
    """dump_request_dir and requests should be overriden in subclass or by monkey-patch.
    If dump_request_dir set to a string, requests are dumped to a directory created at this path.
    if pipe_writer is an endpoint of a multiprocessing.Pipe, request data will be sent into it"""

    dump_request_dir = None
    pipe_writer = None

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

        # parse url
        path_parts = parse.urlsplit(self.path)
        self.path_path = path_parts.path
        self.query_params = parse.parse_qs(path_parts.query)
        self.fragment = path_parts.fragment

        self._preprocess_body()
        request_data = self._collect_request_data()
        self._keep_request(request_data)
        self._dump_request(request_data)

    def _preprocess_body(self):
        self.body_size = int(self._headers_iget("content-length", 0))
        self.bbody = self.rfile.read(self.body_size)

    def _collect_request_data(self):
        return {
            "client_address": ("%s:%s" % self.client_address),
            "url": {
                "path": self.path_path,
                "query_params": self.query_params,
                "fragment": self.fragment,
            },
            "method": self.requestline.split(" ")[0],
            "headers": dict(self.headers.items()),
            "body": b64encode(self.bbody).decode() if self.bbody else "",
            "version": self.request_version,
        }

    @classmethod
    def _keep_request(cls, data):
        # if not isinstance(cls.requests, list):
        if cls.pipe_writer is None:
            return

        _logger.info("Sending request data to parent process through pipe")
        cls.pipe_writer.send(data)

    def _dump_request(self, data):
        if not isinstance(self.dump_request_dir, str):
            return

        if not os.path.isdir(self.dump_request_dir):
            _logger.info("Creating directory %s" % self.dump_request_dir)
            os.mkdir(self.dump_request_dir)

        filepath = os.path.join(
            self.dump_request_dir,
            datetime.datetime.strftime(
                datetime.datetime.utcnow(), "%y-%m-%d_%H%M%S.json"
            ),
        )

        _logger.info("Dumping request data to file %s" % filepath)
        with open(filepath, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _flush_response_body(self):
        """write response_body buffer to output stream"""

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
            "request from %s - - %s"
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

        self._preprocess()
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
            _logger.debug("request body", json.loads(self.bbody.decode()))
        else:
            _logger.debug("request body:", self.bbody.decode())

    def dispatch(self):
        _logger.debug("request Content-Type: %s" % self.content_type)
        if re.search(r"\.[a-z0-9]+$", self.path_path):
            return self.serve_file()
        elif self.content_type == "application/x-www-form-urlencoded":
            return self.serve_form()
        elif self.content_type == "application/json":
            return self.serve_json()
        else:
            return 404

    def serve_form(self):
        _logger.debug("request params: %s" % self.query_params)
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
