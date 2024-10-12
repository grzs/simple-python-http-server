from multiprocessing import Process
from time import sleep

from .server import run_listener


class HTTPd:
    def __init__(self, **kwargs):
        self.process = Process(
            target=run_listener, name="httpd", daemon=True, kwargs=kwargs
        )

    def start(self):
        self.process.start()
        return self.process.pid

    def stop(self, timeout=10):
        self.process.terminate()

        seconds = 0
        while self.process.is_alive():
            if not seconds:
                print("waiting for graceful shutdown ...")
            elif seconds == timeout:
                print("timout exceeded, killing process!")
                self.process.kill()
            else:
                print("... %d seconds left" % timeout - seconds)
            sleep(1)
            seconds += 1

        return self.process.exitcode
