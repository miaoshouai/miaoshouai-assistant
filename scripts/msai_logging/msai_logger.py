import datetime
import logging
import logging.handlers
import os
import typing as t

from scripts.msai_utils.msai_singleton import MiaoshouSingleton


class Logger(metaclass=MiaoshouSingleton):
    _dataset = None

    KEY_TRACE_PATH = "trace_path"
    KEY_INFO = "info"
    KEY_ERROR = "error"
    KEY_JOB = "job"

    def _do_init(self, log_folder: str, disable_console_output: bool = False) -> None:
        # Setup trace_path with empty string by default, it will be assigned with valid content if needed
        self._dataset = {Logger.KEY_TRACE_PATH: ""}

        print(f"logs_location: {log_folder}")
        os.makedirs(log_folder, exist_ok=True)

        # Setup basic logging configuration
        logging.basicConfig(level=logging.INFO,
                            filemode='w',
                            format='%(asctime)s - %(filename)s [line:%(lineno)d] - %(levelname)s: %(message)s')

        # Setup info logging
        self._dataset[Logger.KEY_INFO] = logging.getLogger(Logger.KEY_INFO)
        msg_handler = logging.FileHandler(os.path.join(log_folder, "info.log"),
                                          "a",
                                          encoding="UTF-8")
        msg_handler.setLevel(logging.INFO)
        msg_handler.setFormatter(
            logging.Formatter(fmt='%(asctime)s - %(filename)s [line:%(lineno)d] - %(levelname)s: %(message)s'))
        self._dataset[Logger.KEY_INFO].addHandler(msg_handler)

        # Setup error logging
        self._dataset[Logger.KEY_ERROR] = logging.getLogger(Logger.KEY_ERROR)
        error_handler = logging.FileHandler(
            os.path.join(log_folder, f'error_{datetime.date.today().strftime("%Y%m%d")}.log'),
            mode="a",
            encoding='UTF-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter(
                fmt=f"{self._dataset.get('trace_path')}:\n "
                    f"%(asctime)s - %(filename)s [line:%(lineno)d] - %(levelname)s: %(message)s"))
        self._dataset[Logger.KEY_ERROR].addHandler(error_handler)

        # Setup job logging
        self._dataset[Logger.KEY_JOB] = logging.getLogger(Logger.KEY_JOB)
        job_handler = logging.FileHandler(os.path.join(log_folder, "jobs.log"),
                                          mode="a",
                                          encoding="UTF-8")
        self._dataset[Logger.KEY_JOB].addHandler(job_handler)

        for k in [Logger.KEY_INFO, Logger.KEY_JOB, Logger.KEY_ERROR]:
            l: logging.Logger = self._dataset[k]
            l.propagate = not disable_console_output

    def __init__(self, log_folder: str = None, disable_console_output: bool = False) -> None:
        if self._dataset is None:
            try:
                self._do_init(log_folder=log_folder, disable_console_output=disable_console_output)
            except Exception as e:
                print(e)

    def update_path_info(self, current_path: str) -> None:
        self._dataset[Logger.KEY_TRACE_PATH] = current_path

    def callback_func(self, exc_type: t.Any, exc_value: t.Any, exc_tracback: t.Any) -> None:
        self._dataset[Logger.KEY_JOB].error(f"job failed for {self._dataset[Logger.KEY_TRACE_PATH]}")
        self._dataset[Logger.KEY_INFO].error(f"{self._dataset[Logger.KEY_TRACE_PATH]}\n, callback_func: ",
                                             exc_info=(exc_type, exc_value, exc_tracback))

    def debug(self, fmt, *args, **kwargs) -> None:
        l: logging.Logger = self._dataset[Logger.KEY_INFO]
        l.debug(fmt, *args, **kwargs, stacklevel=2)

    def info(self, fmt, *args, **kwargs) -> None:
        l: logging.Logger = self._dataset[Logger.KEY_INFO]
        l.info(fmt, *args, **kwargs, stacklevel=2)

    def warn(self, fmt, *args, **kwargs) -> None:
        l: logging.Logger = self._dataset[Logger.KEY_INFO]
        l.warn(fmt, *args, **kwargs, stacklevel=2)

    def error(self, fmt, *args, **kwargs) -> None:
        l: logging.Logger = self._dataset[Logger.KEY_ERROR]
        l.error(fmt, *args, **kwargs, stacklevel=2)

    def job(self, fmt, *args, **kwargs) -> None:
        l: logging.Logger = self._dataset[Logger.KEY_JOB]
        l.info(fmt, *args, **kwargs, stacklevel=2)


