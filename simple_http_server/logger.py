import os
from logging import StreamHandler, Formatter, INFO

loghandler = StreamHandler()
logformatter = Formatter(
    "{asctime} {name:26} ({process}) {levelname:>8} : {message}", style="{"
)
loghandler.setFormatter(logformatter)

if (loglevel := os.environ.get("HTTPD_LOGLEVEL")) not in [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]:
    loglevel = INFO
