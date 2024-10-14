from http.server import HTTPServer, ThreadingHTTPServer

from signal import Signals, SIGINT
from selectors import DefaultSelector, EVENT_READ
from multiprocessing import Process

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
        self, address="", port=8000, request_handler=RequestHandler, kill_timeout=10
    ):
        self.httpd = SERVER_CLASS((address, port), request_handler)

        self.selector = DefaultSelector()
        self.selector.register(self.httpd, EVENT_READ)

        self.kill_timeout = kill_timeout
        self.daemon = Process(
            target=self.listen_forever,
            name="httpd",
            daemon=True,
        )

    def __del__(self):
        self.stop()
        self.httpd.server_close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.__del__()

    def listen_forever(self):
        with SignalHandler(port=self.httpd.server_port + 1) as sh_client:
            self.selector.register(sh_client, EVENT_READ)
            self._listener_loop(sh_client)
            self.selector.unregister(sh_client)

    def _listener_loop(self, sh_client):
        """I/O multiplexing loop, exiting when receiving signal from signal_handler."""
        sigint_count = 0
        _logger.debug("Entering I/O multiplexing loop")
        while True:
            for key, _ in self.selector.select():
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
                if key.fileobj == self.httpd:
                    _logger.debug("Request received, passing to handler")
                    self.httpd.handle_request()

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
                _logger.debug("... %d seconds left" % (self.kill_timeout - seconds))
            sleep(1)
            seconds += 1

        _logger.info("Server exited with code: %s" % self.daemon.exitcode)
        return self.daemon.exitcode

    def is_alive(self):
        return self.daemon.is_alive()


if __name__ == "__main__":
    _logger.info("Starting HTTP server in foreground")
    HTTPd().listen_forever()
