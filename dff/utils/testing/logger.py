from logging import Formatter, DEBUG, INFO, Logger, StreamHandler
from sys import stdout


class ConsoleFormatter(Formatter):
    FORMATTERS = {
        DEBUG: Formatter("%(message)s"),
        INFO: Formatter("INFO: %(message)s"),
        "DEFAULT": Formatter("%(name)s - %(levelname)s - %(message)s"),
    }

    def format(self, record):
        formatter = self.FORMATTERS.get(record.levelno, self.FORMATTERS["DEFAULT"])
        return formatter.format(record)

    @staticmethod
    def configure_logger(logger: Logger):
        handler = StreamHandler(stdout)
        handler.setLevel(DEBUG)
        handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)
        logger.setLevel(DEBUG)
