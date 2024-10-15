# Run server in foreground #

```
python3 -m simple_http_server.httpd
```

# Environment Variables #

```
HTTPD_LOGLEVEL
HTTPD_TEST_KEEP_DUMP_FILES
```

# Testing #

```
HTTPD_LOGLEVEL=DEBUG python -m unittest -q
```


# Examples #

```
from http.server import HTTPServer, SimpleHTTPRequestHandler
from simple_http_server.request_handler import RequestHandler
from simple_http_server.httpd import HTTPd

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
