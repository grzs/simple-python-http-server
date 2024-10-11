import requests

from simple_http_server import httpd
from time import sleep


def main():
    print("Starting server")
    pid = httpd.start()
    print("Server started (pid: %d)" % pid)
    sleep(3)
    print("Killing server")
    exitcode = httpd.stop()
    print("Server is exited with code:", (exitcode if exitcode is not None else "N/A"))


if __name__ == "__main__":
    main()
