# Examples #

```
from http.server import HTTPServer, SimpleHTTPRequestHandler
from simple_http_server.handler import RequestHandler
from simple_http_server.daemon import HTTPd

from time import sleep

import logging

logging.getLogger("simple_http_server").setLevel(logging.INFO)


def run_simple(address="", port=8000):
    httpd = HTTPServer((address, port), SimpleHTTPRequestHandler)
    httpd.serve_forever()


# it's possible to start and stop daemon using a context manager
def start_do_something_and_exit(timeout=3):
    with HTTPd(handler=RequestHandler) as httpd:
        # here a request can be sent
        while timeout:
            print("alive?", httpd.is_alive())
            sleep(1)
            timeout -= 1


if __name__ == "__main__":
    start_do_something_and_exit()
```
