import os
import pickle
import queue
import time
import typing as t
from pathlib import Path
from urllib.parse import urlparse

from sha256bit import Sha256bit
import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util import Retry

import scripts.msai_utils.msai_toolkit as toolkit
from scripts.msai_logging.msai_logger import Logger
from scripts.download.resume_checkpoint import ResumeCheckpoint


class MiaoshouFileDownloader(object):
    CHUNK_SIZE = 1024 * 1024

    def __init__(self, target_url: str = None,
                 local_file: str = None, local_directory: str = None, estimated_total_length: float = 0.,
                 expected_checksum: str = None,
                 channel: queue.Queue = None,
                 max_retries=5) -> None:
        self.logger = Logger()

        self.target_url: str = target_url
        self.local_file: str = local_file
        self.local_directory = local_directory
        self.expected_checksum = expected_checksum
        self.max_retries = max_retries

        self.accept_ranges: bool = False
        self.estimated_content_length = estimated_total_length
        self.content_length: int = -1
        self.finished_chunk_size: int = 0

        self.channel = channel  # for communication

        # Support 3 retries and backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # inform message receiver at once
        if self.channel:
            self.channel.put_nowait((
                self.target_url,
                self.finished_chunk_size,
                self.estimated_content_length,
            ))

    # Head request to get file-length and check whether it supports ranges.
    def get_file_info_from_server(self, target_url: str) -> t.Tuple[bool, float]:
        try:
            headers = {"Accept-Encoding": "identity"}  # Avoid dealing with gzip
            response = requests.head(target_url, headers=headers, allow_redirects=True, timeout=10)
            response.raise_for_status()
            content_length = None
            if "Content-Length" in response.headers:
                content_length = int(response.headers['Content-Length'])
            accept_ranges = (response.headers.get("Accept-Ranges") == "bytes")
            return accept_ranges, float(content_length)
        except Exception as ex:
            self.logger.error(f"HEAD Request Error: {ex}")
            return False, self.estimated_content_length

    def download_file_full(self, target_url: str, local_filepath: str) -> t.Optional[str]:
        try:
            checksum = Sha256bit()
            checksum._verbose = False

            headers = {"Accept-Encoding": "identity"}  # Avoid dealing with gzip

            with tqdm(total=self.content_length, unit="byte", unit_scale=1, colour="GREEN",
                      desc=os.path.basename(self.local_file)) as progressbar, \
                    self.session.get(target_url, headers=headers, stream=True, timeout=5) as response, \
                    open(local_filepath, 'wb') as file_out:
                response.raise_for_status()

                for chunk in response.iter_content(MiaoshouFileDownloader.CHUNK_SIZE):
                    file_out.write(chunk)
                    checksum.update(chunk)
                    progressbar.update(len(chunk))
                    self.update_progress(len(chunk))
                    try:
                        checksum.update(chunk)
                    except Exception as err:
                        self.logger.error(f"checksum error {err}")
        except Exception as ex:
            self.logger.error(f"Download error: {ex}")
            return None

        return checksum.hexdigest()

    def download_file_resumable(self, target_url: str, local_filepath: str) -> t.Optional[str]:
        # Always go off the checkpoint as the file was flushed before writing.
        download_checkpoint = local_filepath + ".downloading"
        try:
            resume_point, checksum = pickle.load(open(download_checkpoint, "rb"))
            assert os.path.exists(local_filepath)  # catch checkpoint without file
            self.logger.info("File already exists, resuming download.")
        except Exception as e:
            self.logger.warn(f"failed to load downloading checkpoint - {download_checkpoint} due to {e}")
            resume_point = 0
            checksum = Sha256bit()
            checksum._verbose = False
            if os.path.exists(local_filepath):
                os.remove(local_filepath)
            Path(local_filepath).touch()

        assert (resume_point < self.content_length)

        self.finished_chunk_size = resume_point

        # Support resuming
        headers = {"Range": f"bytes={resume_point}-", "Accept-Encoding": "identity"}
        try:
            with tqdm(total=self.content_length, unit="byte", unit_scale=1, colour="GREEN",
                      desc=os.path.basename(self.local_file)) as progressbar, \
                    self.session.get(target_url, headers=headers, stream=True, timeout=5) as response, \
                    open(local_filepath, 'r+b') as file_out:
                response.raise_for_status()
                self.update_progress(resume_point)
                file_out.seek(resume_point)

                for chunk in response.iter_content(MiaoshouFileDownloader.CHUNK_SIZE):
                    file_out.write(chunk)
                    file_out.flush()
                    resume_point += len(chunk)
                    checksum.update(chunk)
                    pickle.dump((resume_point, checksum), open(download_checkpoint, "wb"))
                    progressbar.update(len(chunk))
                    self.update_progress(len(chunk))
                    try:
                        checksum.update(chunk)
                        ResumeCheckpoint.store_resume_checkpoint(resume_point, checksum, download_checkpoint)
                    except Exception as err:
                        self.logger.error(f"failed to save checkpoint {err}")

                # Only remove checkpoint at full size in case connection cut
                if os.path.getsize(local_filepath) == self.content_length:
                    os.remove(download_checkpoint)
                else:
                    return None

        except Exception as ex:
            self.logger.error(f"Download error: {ex}")
            return None

        return checksum.hexdigest()

    def update_progress(self, finished_chunk_size: int) -> None:
        self.finished_chunk_size += finished_chunk_size

        if self.channel:
            self.channel.put_nowait((
                self.target_url,
                self.finished_chunk_size,
                self.content_length,
            ))

    # In order to avoid leaving extra garbage meta files behind this
    # will overwrite any existing files found at local_file. If you don't want this
    # behaviour you can handle this externally.
    # local_file and local_directory could write to unexpected places if the source
    # is untrusted, be careful!
    def download_file(self) -> bool:
        success = False
        try:
            # Need to rebuild local_file_final each time in case of different urls
            if not self.local_file:
                specific_local_file = os.path.basename(urlparse(self.target_url).path)
            else:
                specific_local_file = self.local_file

            download_temp_dir = toolkit.get_user_temp_dir()
            toolkit.assert_user_temp_dir()

            if self.local_directory:
                os.makedirs(self.local_directory, exist_ok=True)

            specific_local_file = os.path.join(download_temp_dir, specific_local_file)

            self.accept_ranges, self.content_length = self.get_file_info_from_server(self.target_url)
            self.logger.info(f"Accept-Ranges: {self.accept_ranges}. content length: {self.content_length}")
            if self.accept_ranges and self.content_length:
                download_method = self.download_file_resumable
                self.logger.info("Server supports resume")
            else:
                download_method = self.download_file_full
                self.logger.info(f"Server doesn't support resume.")

            for i in range(self.max_retries):
                self.logger.info(f"Download Attempt {i + 1}")
                checksum = download_method(self.target_url, specific_local_file)
                if checksum:
                    match = ""
                    if self.expected_checksum:
                        match = ", Checksum Match"

                    if self.expected_checksum and self.expected_checksum != checksum:
                        self.logger.info(f"Checksum doesn't match. Calculated {checksum} "
                                         f"Expecting: {self.expected_checksum}")
                    else:
                        self.logger.info(f"Download successful{match}. Checksum {checksum}")
                        success = True
                        break
                time.sleep(1)

            if success:
                self.logger.info(f"{self.target_url} [DOWNLOADED COMPLETELY]")
                if self.local_directory:
                    target_local_file = os.path.join(self.local_directory, self.local_file)
                else:
                    target_local_file = self.local_file
                toolkit.move_file(specific_local_file, target_local_file)
            else:
                self.logger.info(f"{self.target_url} [  FAILED  ]")

        except Exception as ex:
            self.logger.error(f"Unexpected Error: {ex}")  # Only from block above
        finally:
            ResumeCheckpoint.store_version_info(local_filepath)


        return success
