import logging
import sys


def get_auto_arg() -> bool:
    return "-a" in sys.argv[1:]


class ConsoleFormatter(logging.Formatter):
    FORMATTERS = {
        logging.DEBUG: logging.Formatter("%(message)s"),
        logging.INFO: logging.Formatter("INFO: %(message)s"),
        "DEFAULT": logging.Formatter("%(name)s - %(levelname)s - %(message)s"),
    }

    def format(self, record):
        formatter = self.FORMATTERS.get(record.levelno, self.FORMATTERS["DEFAULT"])
        return formatter.format(record)
