import os
import pathlib
import glob
import pickle
import typing as t
from hashlib import sha256

from scripts.msai_logging.msai_logger import Logger

logger = Logger()


class ResumeCheckpoint(object):
    VERSION_FILENAME = ".version"
    VERSION = "version 2.0"

    @staticmethod
    def load_resume_checkpoint(filename: str) -> int:
        resume_point = 0
        try:
            # get resume_point from foobar.downloading file
            with open(filename, "rb") as file:
                resume_point = pickle.load(file)
        except Exception as ex:
            logger.error(f"load_resume_checkpoint err: {ex}")
        finally:
            return resume_point

    @staticmethod
    def store_resume_checkpoint(resume_point: int, filename: str) -> bool:
        try:
            with open(filename, "wb") as file:
                pickle.dump(resume_point, file)
                return True
        except Exception as ex:
            logger.error(f"store_resume_checkpoint err: {ex}")
            return False

    @staticmethod
    def cleanup_checkpoints_if_needed(checkpoint_folder: str) -> None:
        version_file = os.path.join(checkpoint_folder, ResumeCheckpoint.VERSION_FILENAME)
        if os.path.isfile(version_file):
            logger.info(f"already {ResumeCheckpoint.VERSION}")
            return

        for file in glob.glob(os.path.join(checkpoint_folder, "*.downloading")):
            print(f"delete checkpoint file with old version: {file}")
            os.remove(file)

    @staticmethod
    def store_version_info(checkpoint_folder: str) -> bool:
        try:
            with open(os.path.join(checkpoint_folder, ResumeCheckpoint.VERSION_FILENAME), "wb") as file:
                footprint = ''' "version": "{}" '''.format(ResumeCheckpoint.VERSION)
                footprint = "{ " + footprint + " }"
                file.write(footprint.encode())
                return True
        except Exception as ex:
            logger.error(f"store_version_info err: {ex}")

    @staticmethod
    def calculate_hash_of_file(filepath: str) -> t.Optional[str]:
        chunk_size = 1024

        try:
            hasher = sha256()
            with open(filepath, "rb") as file:
                while True:
                    data = file.read(chunk_size)
                    if not data:
                        break
                    hasher.update(data)

                return hasher.hexdigest()
        except Exception:
            return None


if __name__ == "__main__":
    checkpoint_dir = "/tmp/miaomiao_download"
    os.makedirs(checkpoint_dir, exist_ok=True)

    ResumeCheckpoint.cleanup_checkpoints_if_needed(checkpoint_dir)
    ResumeCheckpoint.store_version_info(checkpoint_dir)

    pathlib.Path(checkpoint_dir, "one.downloading").touch(exist_ok=True)
    pathlib.Path(checkpoint_dir, "two.downloading").touch(exist_ok=True)
    pathlib.Path(checkpoint_dir, "three.downloading").touch(exist_ok=True)

    print("two.downloading: {}".format(
        ResumeCheckpoint.calculate_hash_of_file("/tmp/miaomiao_download/three.downloading")))

