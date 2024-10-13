from http.server import HTTPServer, ThreadingHTTPServer

import signal
import socket
from selectors import DefaultSelector, EVENT_READ
from multiprocessing import Process

from time import sleep
import os
import logging

from .handler import RequestHandler
from .logger import loghandler, loglevel

_logger = logging.getLogger(
    os.path.basename(__file__) if __name__ == "__main__" else __name__
)
_logger.addHandler(loghandler)
_logger.setLevel(loglevel)

SERVER_CLASS = HTTPServer if os.environ.get("DEBUG") else ThreadingHTTPServer


class HTTPd:
    def __init__(
        self, address="", port=8000, request_handler=RequestHandler, kill_timeout=10
    ):
        self.kill_timeout = kill_timeout
        self.http_server = SERVER_CLASS((address, port), request_handler)
        self.daemon = Process(
            target=self.listen_forever,
            name="httpd",
            daemon=True,
        )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()

    def listen_forever(self):
        """Safe listener loop.
        1. creating a socket pair (like a directed pipe with one end for write, the other for read)
        2. define a signal handler that writes a binary zero to the socket
        3. register the handler to interrupt events
        4. create a selector and register the read end of the socket, and the http server
        5. check the registered endpoints in an infinite loop,
           which breaks if data appears on the socket
        """
        # 1
        interrupt_read, interrupt_write = socket.socketpair()

        # 2
        def signal_handler(signum, frame):
            _logger.debug("HTTPd signal handler called with signal %d" % signum)
            # sending zero to the other end, that will break event listener loop
            interrupt_write.send(b"\0")

        # 3
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 4
        selector = DefaultSelector()
        selector.register(interrupt_read, EVENT_READ)
        selector.register(self.http_server, EVENT_READ)

        # 5
        _logger.debug("Entering to listener loop")
        while True:
            for key, _ in selector.select():
                if key.fileobj == interrupt_read:
                    # receiving one byte
                    interrupt_read.recv(1)
                    _logger.debug("Interrput signal received, returning from listener loop")
                    return
                if key.fileobj == self.http_server:
                    _logger.debug("Request received, passing to handler")
                    self.http_server.handle_request()

    def start(self):
        """Starts the listener as a child process"""
        self.daemon.start()
        _logger.info("Server started (pid: %d)" % self.daemon.pid)
        return self.daemon.pid

    def stop(self):
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
                _logger.debug("... %d seconds left" % self.kill_timeout - seconds)
            sleep(1)
            seconds += 1

        _logger.info("Server exited with code: %s" % self.daemon.exitcode)
        return self.daemon.exitcode

    def is_alive(self):
        return self.daemon.is_alive()


if __name__ == "__main__":
    _logger.info("Starting HTTP server in foreground")
    HTTPd().listen_forever()
