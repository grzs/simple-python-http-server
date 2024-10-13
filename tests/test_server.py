import os
from time import sleep
from urllib import request
from urllib.error import URLError

from simple_http_server.daemon import HTTPd

import logging

# logging
_logger = logging.getLogger(os.path.basename(__file__))


def set_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "{asctime} {name:25} ({process}) {levelname:>6} : {message}", style="{"
        )
    )
    _logger.addHandler(handler)

    if (level := os.environ.get("LOGLEVEL")) not in ["INFO", "ERROR", "DEBUG", "WARNING"]:
        level = logging.INFO

    _logger.setLevel(level)
    logging.getLogger("simple_http_server").setLevel(level)


def main():
    address = "localhost"
    port = 8000
    base_url = f"http://{address}:{port}"

    # start server
    httpd = HTTPd(address=address, port=port)
    _logger.debug("Starting HTTP server")
    httpd.start()

    # probe connection
    req_head = request.Request(base_url, method="HEAD")
    timeout = 3
    attempt_nr = 0
    while attempt_nr < timeout:
        attempt_nr += 1
        _logger.info("Probing connection (attempt #%d) ..." % attempt_nr)
        try:
            request.urlopen(req_head)
        except URLError:
            _logger.info("... not ready yet")
        else:
            _logger.info("... ready!")
            break
        sleep(1)

    # test request
    path = "/foo/bar"
    req = request.Request(f"{base_url}{path}")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req) as f:
        _logger.info("response body: %s" % f.read(300).decode())

    # stop server
    _logger.debug("Stopping HTTP server")
    httpd.stop()


if __name__ == "__main__":
    set_logging()
    main()
