import os
from logging import StreamHandler, Formatter, INFO

_format_str = "{asctime} ({process}) {name:%d} {levelname:>8} : {message}" % (len(__name__) + 5)
loghandler = StreamHandler()
logformatter = Formatter(_format_str, style="{")
loghandler.setFormatter(logformatter)

if (loglevel := os.environ.get("HTTPD_LOGLEVEL")) not in [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]:
    loglevel = INFO
