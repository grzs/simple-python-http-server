from time import sleep
from urllib import request
from urllib.error import URLError

from simple_http_server.daemon import HTTPd


def main():
    address = "localhost"
    port = 8000
    base_url = f"http://{address}:{port}"

    # start server
    httpd = HTTPd(address=address, port=port)
    print("Starting server")
    pid = httpd.start()
    print("Server started (pid: %d)" % pid)

    # probe connection
    req_head = request.Request(base_url, method="HEAD")
    timeout = 3
    attempt_nr = 0
    while attempt_nr < timeout:
        attempt_nr += 1
        print(f"Probing connection (attempt #{attempt_nr}) ...")
        try:
            request.urlopen(req_head)
        except URLError:
            print("... not ready yet")
        else:
            print("... ready!")
            break
        sleep(1)

    # test request
    path = "/foo/bar"
    req = request.Request(f"{base_url}{path}")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req) as f:
        print("body: ", f.read(300).decode())

    # stop server
    print("Stopping server")
    exitcode = httpd.stop()
    print("Server is exited with code:", (exitcode if exitcode is not None else "N/A"))


if __name__ == "__main__":
    main()
