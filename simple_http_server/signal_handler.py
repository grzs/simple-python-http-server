import signal
import socket
import logging

from .log_handler import loghandler, loglevel

_logger = logging.getLogger(__name__)
_logger.addHandler(loghandler)
_logger.setLevel(loglevel)


class SignalHandler:
    def __init__(self, address="127.0.0.1", port=8001, signals=None):
        signals = signals or [signal.SIGINT, signal.SIGTERM]
        self.client_connections = []
        self.clients = []

        # register signal handler
        for sig in signals:
            # TODO: check if it's a signal
            signal.signal(sig, self._handler)

        # init server
        _logger.debug("Creating server listening at %s:%s" % (address, port))
        self.server = socket.create_server((address, port))
        self.server.listen()

    def __del__(self):
        self._close()

    def __enter__(self):
        return self.client_create()

    def __exit__(self, *args, **kwargs):
        self.__del__()

    def _accept_and_register(self):
        _logger.debug("Accepting connection")
        client_conn, _ = self.server.accept()  # blocking!!!
        self.client_connections.append(client_conn)
        _logger.debug("Registered connection from %s:%s" % client_conn.getpeername())

    def _close_connection(self, client_address):
        _logger.debug("Closing connection to client at %s:%s" % client_address)
        # find connection
        for client_conn in self.client_connections:
            if client_conn.getpeername() == client_address:
                client_conn.shutdown(socket.SHUT_RDWR)
                client_conn.close()
                self.client_connections.remove(client_conn)
                return

    def _close_all_connections(self):
        _logger.debug("Closing client connections")
        self._delete_sockets(self.client_connections)

    def _delete_all_clients(self):
        _logger.debug("Deleting clients")
        self._delete_sockets(self.clients)

    @staticmethod
    def _delete_sockets(_sockets):
        while _sockets:
            _socket = _sockets.pop()
            try:
                _socket.shutdown(socket.SHUT_RDWR)
                _socket.close()
            except Exception as e:
                _logger.warning(e)

    def _handler(self, signum, frame):
        _logger.debug(
            "Signal handler called with signal %s" % signal.Signals(signum).name
        )
        # sending signum to clients
        for index, client_conn in enumerate(self.client_connections):
            try:
                client_conn.send(signum.to_bytes(1, "big"))
            except Exception as e:
                _logger.error(e)
                self.client_connections.pop(index)

    def _close(self):
        _logger.debug("shutting down ...")
        self._close_all_connections()
        self._delete_all_clients()
        self.server.shutdown(socket.SHUT_RDWR)
        self.server.close()
        _logger.debug("... shutdown finished")

    # client helpers
    def client_create(self):
        """create client socket, connect to server and ask it to accept connection"""
        _logger.debug("Creating client")
        client = socket.create_connection(self.server.getsockname())
        self._accept_and_register()
        self.clients.append(client)
        return client

    def client_delete(self, client):
        # TODO: check if it's a socket object
        _logger.debug("Deleting client")
        self._close_connection(client.getsockname())
        client.shutdown(socket.SHUT_RDWR)
        client.close()
