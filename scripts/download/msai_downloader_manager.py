import asyncio
import os.path
import queue
import time
import requests
import typing as t
from threading import Thread, Lock

from scripts.download.msai_file_downloader import MiaoshouFileDownloader
from scripts.msai_logging.msai_logger import Logger
from scripts.msai_utils.msai_singleton import MiaoshouSingleton
import scripts.msai_utils.msai_toolkit as toolkit
from urllib.request import Request, urlopen


class DownloadingEntry(object):
    def __init__(self, target_url: str = None, local_file: str = None,
                 local_directory: str = None, estimated_total_size: float = 0., expected_checksum: str = None):
        self._target_url = target_url
        self._local_file = local_file
        self._local_directory = local_directory
        self._expected_checksum = expected_checksum

        self._estimated_total_size = estimated_total_size
        self._total_size = 0
        self._downloaded_size = 0

        self._downloading = False
        self._failure = False

    @property
    def target_url(self) -> str:
        return self._target_url

    @property
    def local_file(self) -> str:
        return self._local_file

    @property
    def local_directory(self) -> str:
        return self._local_directory

    @property
    def expected_checksum(self) -> str:
        return self._expected_checksum

    @property
    def total_size(self) -> int:
        return self._total_size

    @total_size.setter
    def total_size(self, sz: int) -> None:
        self._total_size = sz

    @property
    def downloaded_size(self) -> int:
        return self._downloaded_size

    @downloaded_size.setter
    def downloaded_size(self, sz: int) -> None:
        self._downloaded_size = sz

    @property
    def estimated_size(self) -> float:
        return self._estimated_total_size

    def is_downloading(self) -> bool:
        return self._downloading

    def start_download(self) -> None:
        self._downloading = True

    def update_final_status(self, result: bool) -> None:
        self._failure = (result is False)
        self._downloading = False

    def is_failure(self) -> bool:
        return self._failure


class AsyncLoopThread(Thread):
    def __init__(self):
        super(AsyncLoopThread, self).__init__(daemon=True)
        self.loop = asyncio.new_event_loop()
        self.logger = Logger()
        self.logger.info("looper thread is created")

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.logger.info("looper thread is running")
        self.loop.run_forever()


class MiaoshouDownloaderManager(metaclass=MiaoshouSingleton):
    _downloading_entries: t.Dict[str, DownloadingEntry] = None

    def __init__(self):
        if self._downloading_entries is None:
            self._downloading_entries = {}
            self.message_queue = queue.Queue()

            self.logger = Logger()
            self.looper = AsyncLoopThread()
            self.looper.start()
            self.logger.info("download manager is ready")
            self._mutex = Lock()

    def consume_all_ready_messages(self) -> None:
        """
        capture all enqueued messages, this method should not be used if you are iterating over the message queue
        :return:
            None
        :side-effect:
            update downloading entries' status
        """
        while True:
            # self.logger.info("fetching the enqueued message")
            try:
                (aurl, finished_size, total_size) = self.message_queue.get(block=False, timeout=0.2)
                # self.logger.info(f"[+] message ([{finished_size}/{total_size}]   {aurl}")
                try:
                    self._mutex.acquire(blocking=True)
                    self._downloading_entries[aurl].total_size = total_size
                    self._downloading_entries[aurl].downloaded_size = finished_size
                finally:
                    self._mutex.release()
            except queue.Empty:
                break

    def iterator(self) -> t.Tuple[float, float]:

        while True:
            self.logger.info("waiting for incoming message")

            try:
                (aurl, finished_size, total_size) = self.message_queue.get(block=True)
                self.logger.info(f"[+] message ([{finished_size}/{total_size}]   {aurl}")
                try:
                    self._mutex.acquire(blocking=True)
                    self._downloading_entries[aurl].total_size = total_size
                    self._downloading_entries[aurl].downloaded_size = finished_size

                    tasks_total_size = 0.
                    tasks_finished_size = 0.

                    for e in self._downloading_entries.values():
                        tasks_total_size += e.total_size
                        tasks_finished_size += e.downloaded_size

                    yield tasks_finished_size, tasks_total_size
                finally:
                    self._mutex.release()
            except queue.Empty:
                if len(asyncio.all_tasks(self.looper.loop)) == 0:
                    self.logger.info("all downloading tasks finished")
                    break

    async def _submit_task(self, download_entry: DownloadingEntry) -> None:
        try:
            self._mutex.acquire(blocking=True)
            if download_entry.target_url in self._downloading_entries:
                self.logger.warn(f"{download_entry.target_url} is already downloading")
                return
            else:
                download_entry.start_download()
                self._downloading_entries[download_entry.target_url] = download_entry
        finally:
            self._mutex.release()

        file_downloader = MiaoshouFileDownloader(
            target_url=download_entry.target_url,
            local_file=download_entry.local_file,
            local_directory=download_entry.local_directory,
            channel=self.message_queue if download_entry.estimated_size else None,
            estimated_total_length=download_entry.estimated_size,
            expected_checksum=download_entry.expected_checksum,
        )

        result: bool = await self.looper.loop.run_in_executor(None, file_downloader.download_file)

        try:
            self._mutex.acquire(blocking=True)
            self._downloading_entries[download_entry.target_url].update_final_status(result)
        finally:
            self._mutex.release()

    def download(self, source_url: str, target_file: str, estimated_total_size: float,
                 expected_checksum: str = None) -> None:
        self.logger.info(f"start to download '{source_url}'")

        target_dir = os.path.dirname(target_file)
        target_filename = os.path.basename(target_file)
        download_entry = DownloadingEntry(
            target_url=source_url,
            local_file=target_filename,
            local_directory=target_dir,
            estimated_total_size=estimated_total_size,
            expected_checksum=expected_checksum
        )

        asyncio.run_coroutine_threadsafe(self._submit_task(download_entry), self.looper.loop)

    def tasks_summary(self) -> t.Tuple[int, int, str]:
        self.consume_all_ready_messages()

        total_tasks_num = 0
        ongoing_tasks_num = 0
        failed_tasks_num = 0

        try:
            description = "<div>"
            self._mutex.acquire(blocking=True)
            for name, entry in self._downloading_entries.items():
                if entry.estimated_size is None:
                    continue

                total_tasks_num += 1

                if entry.total_size > 0.:
                    description += f"<p>{entry.local_file} ({toolkit.get_readable_size(entry.total_size)}) : "
                else:
                    description += f"<p>{entry.local_file} ({toolkit.get_readable_size(entry.estimated_size)}) : "

                if entry.is_downloading():
                    ongoing_tasks_num += 1
                    finished_percent = entry.downloaded_size/entry.estimated_size * 100
                    description += f'<span style="color:blue;font-weight:bold">{round(finished_percent, 2)} %</span>'
                elif entry.is_failure():
                    failed_tasks_num += 1
                    description += '<span style="color:red;font-weight:bold">failed!</span>'
                else:
                    description += '<span style="color:green;font-weight:bold">finished</span>'
                description += "</p><br>"
        finally:
            self._mutex.release()
            pass

        description += "</div>"
        overall = f"""
                    <h4>
                        <span style="color:blue;font-weight:bold">{ongoing_tasks_num}</span> ongoing, 
                        <span style="color:green;font-weight:bold">{total_tasks_num - ongoing_tasks_num - failed_tasks_num}</span> finished, 
                        <span style="color:red;font-weight:bold">{failed_tasks_num}</span> failed.
                    </h4>
                    <br>
                    <br>
                   """

        return ongoing_tasks_num, total_tasks_num, overall + description


