import signal
import socket
import logging
from collections import namedtuple

from .log_handler import loghandler, loglevel

_logger = logging.getLogger(__name__)
_logger.addHandler(loghandler)
_logger.setLevel(loglevel)

Connection = namedtuple("COnnection", ["reader", "writer"])


class SignalHandler:
    def __init__(self, address="127.0.0.1", port=8001, signals=None):
        signals = signals or [signal.SIGINT, signal.SIGTERM]
        self.connections = []

        # register signal handler
        for sig in signals:
            # TODO: check if it's a signal
            signal.signal(sig, self._handler)

    def _handler(self, signum, frame):
        _logger.debug(
            "Signal handler called with signal %s" % signal.Signals(signum).name
        )
        # sending signum to clients
        for index, conn in enumerate(self.connections):
            try:
                conn.writer.send(signum.to_bytes(1, "big"))
            except Exception as e:
                _logger.error(e)
                self.connections.pop(index)

    def open_connection(self):
        """create socketpair, return reader end"""
        _logger.debug("Creating connection")
        conn = Connection(*socket.socketpair())
        self.connections.append(conn)
        return conn.reader

    def _close_connections(self):
        _logger.debug("Closing connections")
        while self.connections:
            for sock in self.connections.pop():
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()

    def __del__(self):
        try:
            self._close_connections()
        except OSError as e:
            _logger.error(e)

    def __enter__(self):
        return self.open_connection()

    def __exit__(self, *args, **kwargs):
        self.__del__()
