from multiprocessing import Process
from time import sleep
import logging

from .server import run_listener, _loghandler

_logger = logging.getLogger(__name__)
_logger.addHandler(_loghandler)


class HTTPd:
    def __init__(self, **kwargs):
        self.process = Process(
            target=run_listener, name="httpd", daemon=True, kwargs=kwargs
        )

    def start(self):
        self.process.start()
        _logger.info("Server started (pid: %d)" % self.process.pid)
        return self.process.pid

    def stop(self, timeout=10):
        self.process.terminate()

        seconds = 0
        while self.process.is_alive():
            if not seconds:
                _logger.info("waiting for graceful shutdown ...")
            elif seconds == timeout:
                _logger.critical("timout exceeded, killing process!")
                self.process.kill()
            else:
                _logger.debug("... %d seconds left" % timeout - seconds)
            sleep(1)
            seconds += 1

        _logger.info("HTTP server is exited with code: %s" % self.process.exitcode)
        return self.process.exitcode

    def is_alive(self):
        return self.process.is_alive()
