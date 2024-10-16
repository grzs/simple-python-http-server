from http.server import HTTPServer, ThreadingHTTPServer

from signal import Signals, SIGINT
from selectors import DefaultSelector, EVENT_READ
from multiprocessing import Process, Pipe

from urllib import request
from urllib.error import URLError

from time import sleep
import os
import logging

from .request_handler import RequestHandler
from .signal_handler import SignalHandler
from .log_handler import loghandler, loglevel

_logger = logging.getLogger(
    os.path.basename(__file__) if __name__ == "__main__" else __name__
)
_logger.addHandler(loghandler)
_logger.setLevel(loglevel)

SERVER_CLASS = HTTPServer if os.environ.get("DEBUG") else ThreadingHTTPServer


class HTTPd:
    def __init__(
        self,
        address="",
        port=8000,
        request_handler=RequestHandler,
        kill_timeout=10,
        daemon=True,
    ):
        self.address = address
        self.port = port
        self.request_handler = request_handler
        self.pipe_reader, self.pipe_writer = Pipe()
        request_handler.pipe_writer = self.pipe_writer

        self.selector = DefaultSelector()
        self.selector.register(self.pipe_reader, EVENT_READ)

        self.kill_timeout = kill_timeout

        self.daemon = Process(
            target=self.serve_forever,
            name="httpd",
            daemon=True,
        )
        if daemon:
            self.daemon.start()
            self._wait_until_alive()
            _logger.info("Server started (pid: %d)" % self.daemon.pid)
        else:
            _logger.info("Starting HTTP server")
            self.serve_forever()

    def _wait_until_alive(self, timeout=10):
        address = self.address or "localhost"
        req_head = request.Request(f"http://{address}:{self.port}", method="HEAD")

        _logger.info("Waiting for server booting ...")
        while timeout := timeout - 1:
            try:
                if self.daemon.is_alive():
                    request.urlopen(req_head)
                _logger.info("... ready!")
                return
            except URLError as err:
                _logger.warning(err.reason)
            sleep(1)
            _logger.debug("%d second left" % timeout)

    def read_pipe(self, timeout=3):
        _logger.info("Trying to read data sent by the server (timeout: %d)" % timeout)
        for key, _ in self.selector.select(timeout):
            if key.fileobj == self.pipe_reader:
                return self.pipe_reader.recv()
        _logger.warning("Pipe reading timeout reached")
        return False

    def serve_forever(self):
        with SignalHandler(port=self.port + 1) as sh_client:
            httpd = SERVER_CLASS((self.address, self.port), self.request_handler)
            self.selector.register(httpd, EVENT_READ)
            self.selector.register(sh_client, EVENT_READ)
            self._listener_loop(sh_client, httpd)
            self.selector.unregister(sh_client)
            httpd.server_close()

    def _listener_loop(self, sh_client, httpd, timeout=10):
        """I/O multiplexing loop, exiting when receiving signal from signal_handler."""
        sigint_count = 0
        _logger.debug("Entering I/O multiplexing loop")
        while True:
            for key, _ in self.selector.select(timeout):
                if key.fileobj == sh_client:
                    signum = int.from_bytes(sh_client.recv(1), "big")
                    signal_type = Signals(signum)
                    _logger.debug("Signal %s received" % signal_type.name)
                    # here would bu possible some sophisticated event handling
                    if signal_type == SIGINT and not sigint_count:
                        _logger.warning(
                            "Send SIGTERM or press Ctrl-C again for graceful shutdown."
                        )
                        sigint_count += 1
                    else:
                        _logger.debug("Returning from listener loop")
                        return
                if key.fileobj == httpd:
                    _logger.debug("Request received, passing to handler")
                    httpd.handle_request()

    def is_alive(self):
        return self.daemon.is_alive()

    def __del__(self):
        """Sends an interrupt signal to the listener"""
        if not self.daemon.is_alive():
            return

        self.daemon.terminate()

        seconds = 0
        while self.daemon.is_alive():
            if not seconds:
                _logger.info("waiting for graceful shutdown ...")
            elif seconds == self.kill_timeout:
                _logger.critical("timout exceeded, killing process!")
                self.daemon.kill()
            else:
                _logger.debug("... %d seconds left" % (self.kill_timeout - seconds))
            sleep(1)
            seconds += 1

        _logger.info("Server exited with code: %s" % self.daemon.exitcode)

        self.selector.unregister(self.pipe_reader)
        self.pipe_reader.close()
        self.pipe_writer.close()

        return self.daemon.exitcode

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.__del__()


if __name__ == "__main__":
    _logger.info("Starting HTTP server in foreground")
    HTTPd(daemon=False)
