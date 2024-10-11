from multiprocessing import Process
from time import sleep

from .server import run_listener


server_process = Process(target=run_listener, name="httpd", daemon=True)


def start():
    server_process.start()
    return server_process.pid


def stop():
    server_process.terminate()

    while True:
        if not server_process.is_alive():
            break
        print("Server is still alive, waiting for graceful shutdown")
        sleep(1)

    return server_process.exitcode
