import sys
from logging import Logger, StreamHandler, DEBUG, Formatter, INFO
from typing import Optional, Hashable, Tuple, List, Any
from uuid import uuid4

from dff.core.engine.core import Context
from dff.core.pipeline import PollingMessengerInterface


class ConsoleFormatter(Formatter):
    FORMATTERS = {
        DEBUG: Formatter("%(message)s"),
        INFO: Formatter("INFO: %(message)s"),
        "DEFAULT": Formatter("%(name)s - %(levelname)s - %(message)s"),
    }

    def format(self, record):
        formatter = self.FORMATTERS.get(record.levelno, self.FORMATTERS["DEFAULT"])
        return formatter.format(record)


class LoggerMessengerInterface(PollingMessengerInterface):
    def __init__(
        self,
        logger: Optional[Logger] = None,
        ctx_id: Optional[Hashable] = None,
        happy_path: Optional[Tuple[Tuple[str, str], ...]] = None,
    ):
        self._ctx_id = uuid4() if ctx_id is None else ctx_id
        self._happy_path = happy_path
        if happy_path is None:
            self._request_function = lambda: input(">>> ")
            self._request_logging_function = None
            self._response_function = lambda s: print(f"<<< {s}")
        else:
            if logger is None:
                raise Exception("For execution with toy script logger is required!")
            else:
                self.configure_logger(logger)
            happy_path_generator = self._happy_path_iterator(happy_path)
            self._request_function = lambda: next(happy_path_generator)
            self._request_logging_function = lambda s: logger.debug(f"USER: {s}")
            self._response_function = lambda s: logger.debug(f"BOT: {s}")
        self._current_true_response = None

    @staticmethod
    def configure_logger(logger: Logger):
        handler = StreamHandler(sys.stdout)
        handler.setLevel(DEBUG)
        handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)
        logger.setLevel(DEBUG)

    def _happy_path_iterator(self, happy_path: Tuple[Tuple[str, str], ...]):
        for entry in happy_path:
            self._current_true_response = entry[1]
            yield entry[0]

    def _on_exception(self, e: BaseException):
        if isinstance(e, StopIteration):
            pass
        else:
            raise e

    def _request(self) -> List[Tuple[Any, Any]]:
        request = self._request_function()
        if self._request_logging_function is not None:
            self._request_logging_function(request)
        return [(request, self._ctx_id)]

    def _respond(self, response: List[Context]):
        actual_response = response[0].last_response
        if self._current_true_response is not None and actual_response != self._current_true_response:
            raise Exception(f"true_response != out_response: {self._current_true_response} != {actual_response}")
        self._response_function(actual_response)
