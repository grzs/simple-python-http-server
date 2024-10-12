from urllib import request

from simple_http_server.daemon import HTTPd


def main():
    httpd = HTTPd()
    print("Starting server")
    pid = httpd.start()
    print("Server started (pid: %d)" % pid)

    req = request.Request('http://localhost:8000')
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req) as f:
        print("body: ", f.read(300).decode())

    print("Stopping server")
    exitcode = httpd.stop()
    print("Server is exited with code:", (exitcode if exitcode is not None else "N/A"))


if __name__ == "__main__":
    main()
