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


class SignalHandler:
    def __init__(self, signals=None):
        signals = signals or [signal.SIGINT, signal.SIGTERM]

        self.interrupt_read, self.interrupt_write = socket.socketpair()

        for sig in signals:
            # TODO: check if it's a signal
            signal.signal(sig, self._handler)

    def _handler(self, signum, frame):
        _logger.debug(
            "Signal handler called with signal %s" % signal.Signals(signum).name
        )
        # sending signum to the other end
        self.interrupt_write.send(signum.to_bytes(1, "big"))

    def close(self):
        self.interrupt_write.close()
        self.interrupt_read.close()


class HTTPd:
    def __init__(
        self, address="", port=8000, request_handler=RequestHandler, kill_timeout=10
    ):
        self.kill_timeout = kill_timeout
        self.server_params = ((address, port), request_handler)
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
        1. create a signal handler instance and an http server instance
        2. create a selector and register the read end of the signal handler, and the http server
        3. check the registered file objects in an infinite loop (I/O multiplexing),
           which breaks if data appears on the socket
        4. unregister and close httpd and signal handler
        """
        # 1
        signal_handler = SignalHandler()
        httpd = SERVER_CLASS(*self.server_params)

        # 2
        selector = DefaultSelector()
        selector.register(signal_handler.interrupt_read, EVENT_READ)
        selector.register(httpd, EVENT_READ)

        # 3
        sigint_count = 0
        _logger.debug("Entering I/O multiplexing loop")
        while True:
            for key, _ in selector.select():
                if key.fileobj == signal_handler.interrupt_read:
                    signum = int.from_bytes(signal_handler.interrupt_read.recv(1), "big")
                    signal_type = signal.Signals(signum)
                    _logger.debug("Signal %s received" % signal_type.name)
                    # here would bu possible some sophisticated event handling
                    if signal_type == signal.SIGINT and not sigint_count:
                        _logger.warning(
                            "Send SIGTERM or press Ctrl-C again for graceful shutdown."
                        )
                        sigint_count += 1
                    else:
                        _logger.debug("Returning from lisntener loop")
                        return
                if key.fileobj == httpd:
                    _logger.debug("Request received, passing to handler")
                    httpd.handle_request()

        # 4
        selector.unregister(httpd)
        httpd.server_close()

        selector.unregister(signal_handler.interrupt_read)
        signal_handler.close()

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
